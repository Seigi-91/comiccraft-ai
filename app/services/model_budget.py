"""Persistent request reservations. Counts are a guard, never a currency estimate."""
from functools import wraps
from contextvars import ContextVar
from uuid import uuid4
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.orm import ModelBudget,ModelCall
from app.tools.desktop_bridge import task_context,stage_context

reported_usage=ContextVar('reported_usage',default=None)


class RequestLimitExceeded(ValueError):
    pass


async def reserve(kind,model):
    task=task_context.get()
    if task=='standalone':task='standalone:'+uuid4().hex
    async with AsyncSessionLocal() as db:
        if not await db.get(ModelBudget,task):
            db.add(ModelBudget(task_id=task,reserved=0))
            try:await db.commit()
            except IntegrityError:await db.rollback()
        result=await db.execute(update(ModelBudget).where(ModelBudget.task_id==task,ModelBudget.reserved<settings.MAX_MODEL_REQUESTS_PER_TASK).values(reserved=ModelBudget.reserved+1))
        if result.rowcount!=1:
            await db.rollback()
            raise RequestLimitExceeded('已达此任务的模型请求上限；查看调用记录并确认费用后，在设置中提高上限再继续。')
        receipt=ModelCall(id=uuid4().hex,task_id=task,kind=kind,model=str(model),stage=stage_context.get(),status='reserved')
        db.add(receipt);await db.commit();return receipt.id


async def finish(receipt,status,usage=None,error=None):
    async with AsyncSessionLocal() as db:
        row=await db.get(ModelCall,receipt)
        if row:
            row.status=status;row.usage=usage;row.error=error;await db.commit()


def report_usage(data):
    if not isinstance(data,dict):return
    # Store numerical usage only, never provider text or credentials.
    def clean(value):
        return {k:(clean(v) if isinstance(v,dict) else v) for k,v in value.items() if isinstance(v,(dict,int,float)) and not isinstance(v,bool)}
    reported_usage.set(clean(data))


def tracked(kind,enabled):
    def decorate(func):
        @wraps(func)
        async def call(*args,**kwargs):
            if not enabled():return await func(*args,**kwargs)
            default_model=(settings.CODEX_MODEL or 'CLI default') if kind=='image_edit' and settings.IMAGE_EDIT_PROVIDER=='codex_cli' else settings.IMAGE_EDIT_MODEL
            receipt=await reserve(kind,getattr(args[0],'model',default_model) if args else default_model)
            token=reported_usage.set(None)
            try:
                result=await func(*args,**kwargs)
                await finish(receipt,'completed',reported_usage.get())
                return result
            except BaseException as error:
                await finish(receipt,'failed',reported_usage.get(),type(error).__name__)
                raise
            finally:reported_usage.reset(token)
        return call
    return decorate
