import logging
import json
from sqlalchemy import delete, select
from app.db.repositories import ChapterRepository, TaskRepository, CharacterProfileRepository
from app.models.orm import Panel, PanelStatus, Phase, Project, TaskStatus
from app.models.schemas import TaskResponse
from app.orchestrator.engine import create_comic_graph
from app.services.character_details import creative_character
from app.tools.desktop_bridge import PendingChatGPT, task_context

logger = logging.getLogger(__name__)


class GenerateService:
    def __init__(self, db):
        self.session = db
        self.task_repo = TaskRepository(db)
        self.chapter_repo = ChapterRepository(db)

    async def _run_chapter_generation(self, project_id, chapter_id, task_id):
        token = task_context.set(task_id)
        state = {}
        try:
            task = await self.task_repo.get(task_id)
            chapter = await self.chapter_repo.get(chapter_id)
            project = await self.session.get(Project, project_id)
            if not chapter or chapter.project_id != project_id or not project:
                raise ValueError("项目或章节不存在")
            state = dict((task.result or {}).get("state") or {})
            if not state:
                profiles = await CharacterProfileRepository(self.session).list(project_id)
                previous_chapters = await self.chapter_repo.list(project_id)
                previous_context = [
                    {"title": c.title, "outline": c.outline}
                    for c in previous_chapters
                    if c.created_at < chapter.created_at and c.outline
                ][-3:]
                state = {
                    "project_id": project_id,
                    "task_id": task_id,
                    "current_chapter": chapter_id,
                    "inspiration": f"项目：{project.name}。章节：{chapter.title}。\n{project.inspiration or project.description or ''}\n前章事实（保持连续性）：{json.dumps(previous_context, ensure_ascii=False)}",
                    "style_ref_urls": project.style_ref_urls or [],
                    "characters": [await creative_character(self.session, p) for p in profiles],
                    "next_node": "generate_outline",
                    "events": [],
                }
            await self.task_repo.update(
                task_id,
                {"status": TaskStatus.RUNNING, "error_message": None, "result": {"state": state}},
            )
            graph = create_comic_graph()
            async for event in graph.astream(state, stream_mode="updates"):
                for update in event.values():
                    state.update(update)
                await self.task_repo.update(task_id, {"result": {"state": state}})
                phase = state.get("phase")
                if phase in {p.value for p in Phase}:
                    await self.chapter_repo.update(chapter_id, {"phase": Phase(phase)})
            completed = bool(state.get("final_comic")) and state.get("phase") == "completed"
            await self.chapter_repo.update(
                chapter_id,
                {
                    "outline": state.get("outline"),
                    "storyboard": state.get("storyboard"),
                    "dialogues": state.get("dialogues"),
                    "phase": Phase.COMPLETED if completed else Phase.REVIEW,
                },
            )
            # Replace only after a completed graph, preserving prior published art on failure.
            await self.session.execute(delete(Panel).where(Panel.chapter_id == chapter_id))
            from uuid import uuid4

            for panel in state.get("panels", []):
                self.session.add(
                    Panel(
                        id=str(uuid4()),
                        chapter_id=chapter_id,
                        index=panel["index"],
                        image_url=panel["image_url"],
                        status=(
                            PanelStatus.PASSED
                            if panel["status"] == "passed"
                            else PanelStatus.FAILED
                        ),
                        review_result=panel.get("review_result"),
                    )
                )
            await self.session.flush()
            from app.api.routes.editing import snapshot
            task.result = {"state": state, "final_comic": state.get("final_comic")}
            await snapshot(self.session, chapter, [task], "生成完成" if completed else "审核后保存")
            await self.session.commit()
            await self.task_repo.update(
                task_id,
                {
                    "status": TaskStatus.COMPLETED if completed else TaskStatus.NEEDS_HUMAN,
                    "result": {"state": state, "final_comic": state.get("final_comic")},
                },
            )
        except PendingChatGPT as pending:
            await self.task_repo.update(
                task_id,
                {
                    "status": TaskStatus.NEEDS_HUMAN,
                    "result": {
                        "state": state,
                        "pending_job_id": pending.job["id"],
                        "waiting_for": "chatgpt",
                    },
                },
            )
        except Exception as error:
            logger.exception("Chapter generation failed")
            await self.session.rollback()
            await self.task_repo.update(
                task_id,
                {
                    "status": TaskStatus.FAILED,
                    "error_message": str(error),
                    "result": {"state": state},
                },
            )
        finally:
            task_context.reset(token)

    async def get_task(self, task_id):
        task = await self.task_repo.get(task_id)
        return TaskResponse.model_validate(task) if task else None

    async def submit_human_fix(self, task_id, panel_id, instructions, fixed_image_url=None):
        # Explicit retry with revision instructions; retain review history in state.
        task = await self.task_repo.get(task_id)
        if not task or task.status != TaskStatus.NEEDS_HUMAN:
            return None
        state = dict((task.result or {}).get("state") or {})
        if (task.result or {}).get("waiting_for"):
            raise ValueError("请先完成待办 ChatGPT 任务")
        state.update({"next_node": "generate_panels", "retry_count": 0, "human_intervene": False})
        for panel in state.get("panels", []):
            if str(panel["index"]) == panel_id:
                if fixed_image_url:
                    panel["image_url"] = fixed_image_url
                if state.get("review_history"):
                    for review in state["review_history"][-1]["panel_reviews"]:
                        if review["panel_index"] == panel["index"]:
                            review["issues"].append(
                                {
                                    "type": "人工修订",
                                    "severity": "medium",
                                    "description": instructions,
                                    "suggestion": instructions,
                                }
                            )
        if fixed_image_url:
            state["next_node"] = "review_panels"
        await self.task_repo.update(
            task_id, {"result": {"state": state}, "status": TaskStatus.PENDING}
        )
        return TaskResponse.model_validate(task)
