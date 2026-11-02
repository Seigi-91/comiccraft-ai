"""Database-backed duplicate-run protection for the supported single-instance server."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime,timedelta,timezone
from functools import wraps
from uuid import uuid4
from sqlalchemy import update,delete
from sqlalchemy.exc import IntegrityError
from app.db.session import AsyncSessionLocal
from app.models.orm import TaskLease

TTL=120

def now():return datetime.now(timezone.utc).replace(tzinfo=None)


async def claim(task_id,owner):
    async with AsyncSessionLocal() as db:
        if not await db.get(TaskLease,task_id):
            db.add(TaskLease(task_id=task_id,owner=owner,expires_at=now()+timedelta(seconds=TTL)))
            try:await db.commit();return True
            except IntegrityError:await db.rollback();return False
        result=await db.execute(update(TaskLease).where(TaskLease.task_id==task_id,TaskLease.expires_at<=now()).values(owner=owner,expires_at=now()+timedelta(seconds=TTL)))
        await db.commit();return result.rowcount==1


async def renew(task_id,owner):
    async with AsyncSessionLocal() as db:
        result=await db.execute(update(TaskLease).where(TaskLease.task_id==task_id,TaskLease.owner==owner).values(expires_at=now()+timedelta(seconds=TTL)))
        await db.commit();return result.rowcount==1


async def release(task_id,owner):
    async with AsyncSessionLocal() as db:
        await db.execute(delete(TaskLease).where(TaskLease.task_id==task_id,TaskLease.owner==owner));await db.commit()


async def heartbeat(task_id,owner,parent):
    try:
        while True:
            await asyncio.sleep(30)
            if not await renew(task_id,owner):parent.cancel();return
    except asyncio.CancelledError:raise
    except Exception:
        # Do not keep issuing new model requests if the runner cannot renew ownership.
        parent.cancel()


def leased_task(func):
    @wraps(func)
    async def run(*args,**kwargs):
        task_id=kwargs.get('task_id') or args[-1]
        owner=uuid4().hex
        if not await claim(task_id,owner):return
        beat=asyncio.create_task(heartbeat(task_id,owner,asyncio.current_task()))
        try:return await func(*args,**kwargs)
        finally:
            beat.cancel()
            try:await beat
            except asyncio.CancelledError:pass
            await release(task_id,owner)
    return run
