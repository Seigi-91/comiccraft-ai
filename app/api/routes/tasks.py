from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from app.db.session import get_db, AsyncSessionLocal
from app.models.orm import Chapter, Task, TaskStatus
from app.models.schemas import GenerateChapterRequest, HumanFixRequest, TaskResponse
from app.services.generate_service import GenerateService

router = APIRouter()
active_tasks = set()


async def run_generation(project_id, chapter_id, task_id):
    if task_id in active_tasks:
        return
    active_tasks.add(task_id)
    try:
        async with AsyncSessionLocal() as session:
            await GenerateService(session)._run_chapter_generation(project_id, chapter_id, task_id)
    finally:
        active_tasks.discard(task_id)
    from app.services.production_queue import schedule_batches
    await schedule_batches()


@router.post("/generate-chapter", response_model=TaskResponse)
async def generate_chapter(
    data: GenerateChapterRequest, background_tasks: BackgroundTasks, db=Depends(get_db)
):
    chapter = await db.get(Chapter, data.chapter_id)
    if not chapter or chapter.project_id != data.project_id:
        raise HTTPException(404, "章节不属于该项目")
    existing = (
        (
            await db.execute(
                select(Task).where(
                    Task.chapter_id == data.chapter_id,
                    Task.status.in_(
                        [TaskStatus.RUNNING, TaskStatus.PENDING, TaskStatus.NEEDS_HUMAN]
                    ),
                )
            )
        )
        .scalars()
        .first()
    )
    if existing:
        return TaskResponse.model_validate(existing)
    service = GenerateService(db)
    task = await service.task_repo.create(data.project_id, data.chapter_id, "generate_chapter")
    background_tasks.add_task(run_generation, data.project_id, data.chapter_id, task.id)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db=Depends(get_db)):
    task = await GenerateService(db).get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.post("/{task_id}/resume", response_model=TaskResponse)
async def resume_task(task_id: str, background_tasks: BackgroundTasks, db=Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task_id in active_tasks or task.status == TaskStatus.COMPLETED:
        raise HTTPException(409, "任务正在执行或已完成")
    await GenerateService(db).task_repo.update(
        task_id, {"status": TaskStatus.PENDING, "error_message": None}
    )
    background_tasks.add_task(run_generation, task.project_id, task.chapter_id, task_id)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/human-fix", response_model=TaskResponse)
async def submit_human_fix(
    task_id: str, data: HumanFixRequest, background_tasks: BackgroundTasks, db=Depends(get_db)
):
    try:
        task = await GenerateService(db).submit_human_fix(
            task_id, data.panel_id, data.instructions, data.fixed_image_url
        )
    except ValueError as error:
        raise HTTPException(409, str(error))
    if not task:
        raise HTTPException(404, "没有可修订的任务")
    background_tasks.add_task(run_generation, task.project_id, task.chapter_id, task_id)
    return task
