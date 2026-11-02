import base64
import json
from fastapi import Request, APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
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
        "text_base_url": settings.LOCAL_GPT_BASE_URL,
        "text_key_configured": bool(settings.LOCAL_GPT_API_KEY),
        "vision_model": settings.DEFAULT_VISION_MODEL,
        "image_provider": settings.image_provider,
        "image_base_url": settings.IMAGE_API_BASE_URL,
        "image_api_model": settings.IMAGE_API_MODEL,
        "image_key_configured": bool(settings.IMAGE_API_KEY),
        "edit_provider": settings.IMAGE_EDIT_PROVIDER,
        "requires_manual_handoff": settings.AI_PROVIDER == "chatgpt_desktop" or settings.image_provider == "chatgpt_desktop",
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

class ConnectionUpdate(BaseModel):
    image_provider: str | None = None
    text_provider: str | None = None
    text_base_url: str = Field(default="https://api.openai.com/v1", max_length=500)
    text_model: str = Field(default="", max_length=200)
    vision_model: str = Field(default="", max_length=200)
    text_api_key: str | None = Field(default=None, max_length=1000)
    clear_text_key: bool = False
    image_base_url: str = Field(default="https://api.openai.com/v1", max_length=500)
    image_model: str = Field(default="gpt-image-1", min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=1000)
    clear_key: bool = False
    use_for_repairs: bool = True


@router.put("/config")
async def update_connection(data: ConnectionUpdate, request: Request):
    # This unauthenticated app may only change credentials from its local browser.
    from urllib.parse import urlsplit
    from pathlib import Path
    import os
    from app.core.paths import ROOT
    peer = request.client.host if request.client else ''
    host = urlsplit('http://' + request.headers.get('host', '')).hostname
    origin = request.headers.get('origin')
    local = {'localhost', '127.0.0.1', '::1', 'testserver', 'testclient'}
    if not settings.ENABLE_LOCAL_SETTINGS or peer not in local or host not in local:
        raise HTTPException(403, '模型设置仅允许本机访问；远程部署请由管理员配置 .env')
    if origin and urlsplit(origin).hostname not in local:
        raise HTTPException(403, '不允许跨站修改模型设置')
    if active_tasks:
        raise HTTPException(409, '请等待正在生成的任务完成后再切换模型')
    def validate_address(url):
        try:
            address = urlsplit(url)
            valid = address.scheme in {'http', 'https'} and address.hostname and not (address.username or address.password or address.query or address.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise HTTPException(422, 'API 地址必须是无密钥、无查询参数的 http/https 基础地址')

    if any('\n' in value or '\r' in value for value in [data.image_base_url, data.image_model, data.api_key or '', data.text_base_url, data.text_model, data.vision_model, data.text_api_key or '']):
        raise HTTPException(422, '配置不能包含换行')
    values = {}
    if data.image_provider is not None:
        if data.image_provider not in {'chatgpt_desktop', 'openai'}:
            raise HTTPException(422, '未知图片提供方')
        validate_address(data.image_base_url)
        key = None if data.clear_key else (data.api_key or settings.IMAGE_API_KEY)
        values.update(IMAGE_PROVIDER=data.image_provider, IMAGE_API_BASE_URL=data.image_base_url.rstrip('/'),
                      IMAGE_API_MODEL=data.image_model, IMAGE_API_KEY=key)
        if data.use_for_repairs:
            values.update(IMAGE_EDIT_PROVIDER=data.image_provider, IMAGE_EDIT_BASE_URL=values['IMAGE_API_BASE_URL'],
                          IMAGE_EDIT_API_KEY=key, IMAGE_EDIT_MODEL=data.image_model)
    if data.text_provider is not None:
        if data.text_provider not in {'chatgpt_desktop', 'local_http'}:
            raise HTTPException(422, '未知文字提供方')
        validate_address(data.text_base_url)
        if not data.text_model.strip() or not data.vision_model.strip():
            raise HTTPException(422, '请填写文字模型与视觉模型名；可填写相同的多模态模型')
        # Freeze legacy image fallback before changing AI_PROVIDER, so a text-only
        # switch cannot silently reroute images or their credentials.
        if settings.IMAGE_PROVIDER is None and 'IMAGE_PROVIDER' not in values:
            values.update(IMAGE_PROVIDER=settings.image_provider)
            if settings.image_provider == 'openai':
                values.update(IMAGE_API_BASE_URL=settings.LOCAL_GPT_BASE_URL,
                              IMAGE_API_KEY=settings.LOCAL_GPT_API_KEY, IMAGE_API_MODEL=settings.DEFAULT_IMAGE_MODEL)
        values.update(AI_PROVIDER=data.text_provider, LOCAL_GPT_BASE_URL=data.text_base_url.rstrip('/'),
                      LOCAL_GPT_API_KEY=None if data.clear_text_key else (data.text_api_key or settings.LOCAL_GPT_API_KEY),
                      DEFAULT_TEXT_MODEL=data.text_model.strip(), DEFAULT_INFERENCE_MODEL=data.text_model.strip(),
                      DEFAULT_VISION_MODEL=data.vision_model.strip())
    if not values:
        raise HTTPException(422, '请指定要修改的模型连接')
    env_path = ROOT / '.env'
    lines = env_path.read_text(encoding='utf-8').splitlines() if env_path.exists() else []
    lines = [line for line in lines if line.split('=', 1)[0].strip() not in values]
    lines.extend(f'{name}={json.dumps(value or "", ensure_ascii=False)}' for name, value in values.items())
    temporary = env_path.with_suffix('.env.tmp')
    try:
        temporary.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        os.chmod(temporary, 0o600)
        os.replace(temporary, env_path)
    except OSError:
        raise HTTPException(500, '无法保存本机配置，请检查 .env 写入权限')
    for name, value in values.items():
        setattr(settings, name, value)
    return await public_config()
