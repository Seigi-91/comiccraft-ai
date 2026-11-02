from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from app.db.session import get_db, AsyncSessionLocal
from app.models.orm import Chapter, Task, TaskStatus
from app.models.schemas import GenerateChapterRequest, HumanFixRequest, TaskResponse
from app.services.generate_service import GenerateService

router = APIRouter()
active_tasks = set()


from app.services.task_leases import leased_task

@leased_task
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
    from app.models.orm import TaskLease
    from app.services.task_leases import now
    lease=await db.get(TaskLease,task_id)
    if lease and lease.expires_at>now() and task_id not in active_tasks:
        raise HTTPException(409,"任务租约尚未过期；进程中断后最多等待120秒再继续，先核对未确认请求的账单。")
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


@router.post("/{task_id}/continue-automatic",response_model=TaskResponse)
async def continue_automatic(task_id:str,background_tasks:BackgroundTasks,request:Request,db=Depends(get_db)):
    from app.api.local_access import require_local_settings
    require_local_settings(request)
    from app.core.config import settings
    from app.tools.desktop_bridge import read_job,save_job
    from sqlalchemy import update
    task=await db.get(Task,task_id)
    if not task or task.status!=TaskStatus.NEEDS_HUMAN or not (task.result or {}).get('pending_job_id'):
        raise HTTPException(409,'当前任务没有可转换的人工待办')
    from app.models.orm import TaskLease
    from app.services.task_leases import now
    lease=await db.get(TaskLease,task_id)
    if task_id in active_tasks or (lease and lease.expires_at>now()):raise HTTPException(409,'任务正在执行')
    try:job=read_job(task.result['pending_job_id'])
    except FileNotFoundError:raise HTTPException(409,'待办记录不存在')
    provider=settings.image_provider if job['kind']=='image' else settings.AI_PROVIDER
    if provider=='chatgpt_desktop':raise HTTPException(409,'请先在设置中启用当前阶段的自动模型连接')
    if task.type not in {'generate_chapter','edited_chapter','restored_chapter','experiment'}:raise HTTPException(409,'此任务类型暂不支持自动转换')
    result={'state':(task.result or {}).get('state',{}),'superseded_job_id':job['id']}
    changed=await db.execute(update(Task).where(Task.id==task_id,Task.status==TaskStatus.NEEDS_HUMAN).values(status=TaskStatus.PENDING,error_message=None,result=result))
    if changed.rowcount!=1:raise HTTPException(409,'任务状态已变化，请刷新')
    await db.commit()
    job['status']='superseded'
    try:save_job(job)
    except OSError:pass  # Task no longer references it; never fabricate a model reply.
    if task.type=='experiment':
        from app.services.production_queue import run_experiment
        background_tasks.add_task(run_experiment,task_id)
    else:background_tasks.add_task(run_generation,task.project_id,task.chapter_id,task_id)
    await db.refresh(task)
    return TaskResponse.model_validate(task)
