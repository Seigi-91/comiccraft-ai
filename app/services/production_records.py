"""Immutable request context plus evolving outcome; never invent historical settings."""
import hashlib
import json
from copy import deepcopy
from app.db.session import AsyncSessionLocal
from app.models.orm import ProductionRecord,Task
from app.tools.desktop_bridge import task_context,stage_context
from app.core.config import settings
from app.tools.media import local_image_path


def asset_hash(url):
    try:return hashlib.sha256(local_image_path(url).read_bytes()).hexdigest()
    except (ValueError,OSError):return None


async def start_record(prompt, references, model, width, height, style, context):
    task_id=task_context.get();stage=stage_context.get()
    payload={'prompt':prompt,'references':[{'url':u,'sha256':asset_hash(u)} for u in references or []],
             'provider':settings.AI_PROVIDER,'model_requested':model,'parameters_requested':{'width':width,'height':height,'style':style},
             'parameter_semantics':'desktop: prompt constraints, not guaranteed inference parameters' if settings.AI_PROVIDER=='chatgpt_desktop' else 'HTTP: model, n=1 and size sent; style is prompt text',
             'context':deepcopy(context or {}),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
    record_id=hashlib.sha256(json.dumps([task_id,stage,payload],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    async with AsyncSessionLocal() as db:
        row=await db.get(ProductionRecord,record_id)
        if not row:
            task=await db.get(Task,task_id)
            chapter_id=task.chapter_id if task else None
            if task and not chapter_id:chapter_id=(task.result or {}).get('experiment',{}).get('chapter_id')
            try:index=int(stage.split(':')[-1])
            except ValueError:index=(context or {}).get('panel',{}).get('index',-1)
            if stage.startswith('experiment:'):index=(context or {}).get('panel',{}).get('index',index)
            row=ProductionRecord(id=record_id,chapter_id=chapter_id,task_id=task_id,panel_index=index,status='requested',origin='generation',settings_snapshot=payload)
            db.add(row);await db.commit()
    return record_id


async def finish_record(record_id,status,image_url=None,error=None):
    async with AsyncSessionLocal() as db:
        row=await db.get(ProductionRecord,record_id)
        if row:
            row.status=status;row.image_url=image_url
            row.error=error
            await db.commit()
