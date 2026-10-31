import base64
import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from app.agents.skills import catalog
from app.core.config import settings
from app.db.session import get_db
from app.models.orm import Task, TaskStatus
from app.models.schemas import StorySchema, StoryboardSchema, DialogueSchema, ReviewResult
from app.tools.desktop_bridge import read_job, list_jobs, save_job
from app.tools.llm_client import parse_json
from app.tools.media import save_image_bytes
from app.api.routes.tasks import run_generation, active_tasks

router = APIRouter()


@router.get("/config")
async def public_config():
    return {
        "provider": settings.AI_PROVIDER,
        "requires_manual_handoff": settings.AI_PROVIDER == "chatgpt_desktop",
        "description": (
            "ChatGPT 协作模式：复制任务到本机 ChatGPT，再回填 JSON 或上传图片。"
            if settings.AI_PROVIDER == "chatgpt_desktop"
            else "OpenAI 兼容 HTTP 服务"
        ),
        "text_model": settings.DEFAULT_TEXT_MODEL,
        "image_model": settings.DEFAULT_IMAGE_MODEL,
    }


@router.get("/agents")
async def agents():
    return catalog()


@router.get("/jobs")
async def jobs(task_id: str | None = None):
    return list_jobs(task_id)


@router.get("/chapters/{chapter_id}/task", response_model=None)
async def latest_task(chapter_id: str, db=Depends(get_db)):
    task = (
        (
            await db.execute(
                select(Task).where(Task.chapter_id == chapter_id).order_by(Task.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    from app.models.schemas import TaskResponse

    return TaskResponse.model_validate(task) if task else None


@router.post("/uploads")
async def upload(file: UploadFile):
    try:
        data = await file.read(20 * 1024 * 1024 + 1)
        return {"url": save_image_bytes(data)}
    except Exception as error:
        raise HTTPException(422, f"图片无效：{error}")


class JobReply(BaseModel):
    text: str | None = Field(default=None, max_length=200000)
    image_url: str | None = None


@router.post("/jobs/{job_id}/reply")
async def reply(job_id: str, data: JobReply, background_tasks: BackgroundTasks, db=Depends(get_db)):
    try:
        job = read_job(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "任务不存在")
    task = await db.get(Task, job["task_id"])
    if not task or (task.result or {}).get("pending_job_id") != job_id:
        raise HTTPException(409, "此待办已失效")
    if task.id in active_tasks or task.status != TaskStatus.NEEDS_HUMAN:
        raise HTTPException(409, "任务正在执行")
    try:
        if job["kind"] == "image":
            from app.tools.media import local_image_path

            if not data.image_url or not local_image_path(data.image_url).is_file():
                raise ValueError("请上传实际生成的图片")
            response = data.image_url
        else:
            result = parse_json(data.text or "")
            schema = {
                "generate_outline": StorySchema,
                "generate_storyboard": StoryboardSchema,
                "generate_dialogue": DialogueSchema,
                "review_panels": ReviewResult,
            }.get(job["stage"])
            if job["stage"].startswith("bubble_placement:"):
                from app.agents.bubble_placement import PlacementPlan, validate_plan
                plan = PlacementPlan.model_validate(result)
                panel_index = int(job["stage"].split(":")[1])
                source_state = (task.result or {}).get("state", {})
                bubbles = {i:b for i,b in enumerate(source_state.get("dialogues", {}).get("bubbles", [])) if b["panel_index"] == panel_index and b["text"].strip()}
                validate_plan(plan, bubbles)
                result = plan.model_dump()
            if schema:
                result = schema.model_validate(result).model_dump()
            state = (task.result or {}).get("state", {})
            if job["stage"] == "generate_storyboard":
                panels = result["panels"]
                if (
                    not panels
                    or len(panels) > 24
                    or [p["index"] for p in panels] != list(range(len(panels)))
                ):
                    raise ValueError("分镜必须为 1–24 格，index 从 0 连续递增")
            if job["stage"] == "generate_dialogue":
                valid = {p["index"] for p in state["storyboard"]["panels"]}
                if any(
                    b["panel_index"] not in valid or len(b["text"]) > 60 for b in result["bubbles"]
                ):
                    raise ValueError("台词引用无效或单个气泡超过 60 字")
            response = json.dumps(result, ensure_ascii=False)
    except (ValueError, KeyError, ValidationError) as error:
        raise HTTPException(422, str(error))
    job.update({"status": "completed", "response": response})
    save_job(job)
    task.status = TaskStatus.PENDING
    await db.commit()
    if task.type == "experiment":
        from app.services.production_queue import run_experiment
        background_tasks.add_task(run_experiment, task.id)
    else:
        background_tasks.add_task(run_generation, task.project_id, task.chapter_id, task.id)
    return {"status": "accepted"}
