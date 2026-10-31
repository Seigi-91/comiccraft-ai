"""Durable batch state; one dispatcher for the supported single-process server."""
import asyncio
from copy import deepcopy
from uuid import uuid4
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.orm import ProductionBatch,Task,TaskStatus

dispatch_lock=asyncio.Lock()


async def run_experiment(task_id):
    from app.tools.desktop_bridge import task_context,stage_context,PendingChatGPT
    from app.tools.image_gen import ImageGeneratorClient
    from app.api.routes.tasks import active_tasks
    if task_id in active_tasks:return
    active_tasks.add(task_id)
    token=task_context.set(task_id);stage=stage_context.set('experiment:0')
    try:
        async with AsyncSessionLocal() as db:
            task=await db.get(Task,task_id);experiment=deepcopy(task.result['experiment'])
            task.status=TaskStatus.RUNNING;await db.commit()
            try:
                params=experiment['parameters']
                url=await ImageGeneratorClient().generate_image(
                    experiment['prompt'],width=params['width'],height=params['height'],style=params['style'],
                    reference_images=experiment['references'],generation_context=experiment['snapshot'])
                task.result={'experiment':experiment,'candidate_url':url};task.status=TaskStatus.COMPLETED
            except PendingChatGPT as pending:
                task.result={'experiment':experiment,'pending_job_id':pending.job['id'],'waiting_for':'image'}
                task.status=TaskStatus.NEEDS_HUMAN
            except Exception as error:
                task.status=TaskStatus.FAILED;task.error_message=str(error)
            await db.commit()
    finally:
        task_context.reset(token);stage_context.reset(stage);active_tasks.discard(task_id)
    await schedule_batches()


async def schedule_batches():
    dispatch=None
    async with dispatch_lock:
        async with AsyncSessionLocal() as db:
            batches=list((await db.execute(select(ProductionBatch).where(ProductionBatch.status=='running').order_by(ProductionBatch.created_at))).scalars())
            for batch in batches:
                items=deepcopy(batch.items)
                for item in items:
                    if item.get('task_id'):
                        task=await db.get(Task,item['task_id'])
                        item['status']=task.status.value if task else 'failed'
                        item['error']=task.error_message if task else '任务不存在'
                    if item['status']=='failed':batch.status='failed';break
                    if item['status']=='completed':continue
                    if item.get('task_id'):break
                    if item['kind']=='chapter':
                        existing=(await db.execute(select(Task).where(Task.chapter_id==item['chapter_id'],Task.status.in_([TaskStatus.RUNNING,TaskStatus.PENDING,TaskStatus.NEEDS_HUMAN])).order_by(Task.created_at.desc()))).scalars().first()
                        if existing:
                            item.update(task_id=existing.id,status=existing.status.value);break
                    task=Task(id=str(uuid4()),project_id=batch.project_id,chapter_id=item['chapter_id'] if item['kind']=='chapter' else None,
                              type='generate_chapter' if item['kind']=='chapter' else 'experiment',status=TaskStatus.PENDING,
                              result={'experiment':item['experiment']} if item['kind']=='experiment' else None)
                    db.add(task);item.update(task_id=task.id,status='pending')
                    dispatch=(item['kind'],batch.project_id,item['chapter_id'],task.id);break
                if items and all(i['status']=='completed' for i in items):batch.status='completed'
                batch.items=items
                if dispatch:break
            await db.commit()
    if dispatch:
        kind,project_id,chapter_id,task_id=dispatch
        if kind=='chapter':
            from app.api.routes.tasks import run_generation
            await run_generation(project_id,chapter_id,task_id)
        else:await run_experiment(task_id)
