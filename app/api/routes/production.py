import json
from copy import deepcopy
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,BackgroundTasks
from pydantic import BaseModel,Field
from sqlalchemy import select
from app.db.session import get_db
from app.models.orm import ProductionRecord,ProductionBatch,Chapter,Task,Panel,Project
from app.api.routes.editing import context
from app.core.config import settings
from app.services.production_queue import schedule_batches
from app.services.effects import EffectLayer,apply_effects

router=APIRouter()


class EffectRequest(BaseModel):
    layers:list[EffectLayer]=Field(max_length=12)
    expected_version:str | None = None


@router.get('/chapters/{chapter_id}/effects')
async def effects(chapter_id:str,db=Depends(get_db)):
    _,tasks=await context(db,chapter_id)
    from app.api.routes.editing import latest_version
    v=await latest_version(db,chapter_id)
    state=(tasks[0].result or {}).get('state',{}) if tasks else {}
    return {'effects':state.get('effects',{}),'expected_version':v.id if v else None}


@router.post('/chapters/{chapter_id}/panels/{index}/effects/{action}')
async def set_effects(chapter_id:str,index:int,action:str,payload:EffectRequest,db=Depends(get_db)):
    chapter,tasks=await context(db,chapter_id)
    panel=(await db.execute(select(Panel).where(Panel.chapter_id==chapter_id,Panel.index==index))).scalar_one_or_none()
    if not panel:raise HTTPException(404,'分镜不存在')
    layers=[l.model_dump() for l in payload.layers]
    if len({l['id'] for l in layers})!=len(layers):raise HTTPException(422,'图层编号重复')
    if action=='preview':
        from PIL import Image
        from app.tools.media import local_image_path
        from app.core.paths import MEDIA
        with Image.open(local_image_path(panel.image_url)) as source:image=apply_effects(source,layers)
        path=MEDIA/f'effects-preview-{uuid4().hex}.png';image.save(path)
        return {'image_url':'/media/'+path.name}
    if action!='save':raise HTTPException(404,'未知操作')
    from app.api.routes.editing import latest_version,unlocked,compose_chapter
    unlocked(tasks)
    v=await latest_version(db,chapter_id)
    if payload.expected_version!=(v.id if v else None):raise HTTPException(409,'版本已变化，请重新加载特效配置')
    state=(tasks[0].result or {}).get('state',{}) if tasks else {}
    mapping=deepcopy(state.get('effects',{}));mapping[str(index)]=layers
    return await compose_chapter(chapter_id,db,effects=mapping)


@router.get('/chapters/{chapter_id}/records')
async def records(chapter_id:str,db=Depends(get_db)):
    await context(db,chapter_id)
    rows=(await db.execute(select(ProductionRecord).where(ProductionRecord.chapter_id==chapter_id).order_by(ProductionRecord.created_at.desc()).limit(200))).scalars()
    return [{'id':r.id,'task_id':r.task_id,'panel_index':r.panel_index,'status':r.status,'origin':r.origin,'snapshot':r.settings_snapshot,'image_url':r.image_url,'error':r.error,'created_at':r.created_at,'updated_at':r.updated_at} for r in rows]


@router.post('/chapters/{chapter_id}/capture')
async def capture(chapter_id:str,db=Depends(get_db)):
    chapter,tasks=await context(db,chapter_id)
    state=deepcopy((tasks[0].result or {}).get('state',{})) if tasks else {}
    panels=(await db.execute(select(Panel).where(Panel.chapter_id==chapter_id))).scalars()
    from app.services.production_records import asset_hash
    count=0
    for p in panels:
        snap={'captured_now':True,'historical_generation_parameters':'unknown','outline':chapter.outline,'storyboard':chapter.storyboard,
              'dialogues':chapter.dialogues,'characters_from_saved_task':state.get('characters',[]),'effects':state.get('effects',{}).get(str(p.index),[]),'image_sha256':asset_hash(p.image_url)}
        db.add(ProductionRecord(id=str(uuid4()),chapter_id=chapter_id,task_id=tasks[0].id if tasks else 'capture',panel_index=p.index,status='captured',origin='current_capture_not_historical_generation',settings_snapshot=snap,image_url=p.image_url));count+=1
    await db.commit();return {'captured':count}


class BatchRequest(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    chapter_ids:list[str]=Field(min_length=1,max_length=20)


@router.post('/projects/{project_id}/batches')
async def create_batch(project_id:str,payload:BatchRequest,db=Depends(get_db)):
    if len(set(payload.chapter_ids))!=len(payload.chapter_ids):raise HTTPException(422,'章节不能重复')
    for cid in payload.chapter_ids:
        ch=await db.get(Chapter,cid)
        if not ch or ch.project_id!=project_id:raise HTTPException(404,'章节不属于此项目')
    row=ProductionBatch(id=str(uuid4()),project_id=project_id,name=payload.name,status='paused',items=[{'kind':'chapter','chapter_id':cid,'status':'queued'} for cid in payload.chapter_ids])
    db.add(row);await db.commit();return {'id':row.id}


@router.get('/projects/{project_id}/batches')
async def batches(project_id:str,db=Depends(get_db)):
    rows=(await db.execute(select(ProductionBatch).where(ProductionBatch.project_id==project_id).order_by(ProductionBatch.created_at.desc()).limit(50))).scalars();output=[]
    for row in rows:
        items=deepcopy(row.items)
        for item in items:
            if item.get('task_id'):
                task=await db.get(Task,item['task_id'])
                if task:item.update(status=task.status.value,error=task.error_message,candidate_url=(task.result or {}).get('candidate_url'),pending_job_id=(task.result or {}).get('pending_job_id'))
        output.append({'id':row.id,'name':row.name,'status':row.status,'items':items,'created_at':row.created_at})
    return output


@router.post('/batches/{batch_id}/{action}')
async def control(batch_id:str,action:str,background_tasks:BackgroundTasks,db=Depends(get_db)):
    row=await db.get(ProductionBatch,batch_id)
    if not row:raise HTTPException(404,'批次不存在')
    if action=='pause' and row.status=='running':row.status='paused'
    elif action=='cancel':row.status='cancelled'
    elif action=='start' and row.status=='paused':row.status='running'
    elif action=='retry' and row.status=='failed':
        items=deepcopy(row.items)
        for item in items:
            task=await db.get(Task,item['task_id']) if item.get('task_id') else None
            if (not task and item.get('status')=='failed') or (task and task.status.value=='failed'):
                item.update(status='queued');item.pop('task_id',None);item.pop('error',None)
            elif task and task.status.value=='completed':item['status']='completed'
        row.items=items;row.status='running'
    else:raise HTTPException(409,'当前批次状态不支持此操作')
    await db.commit()
    if row.status=='running':background_tasks.add_task(schedule_batches)
    return {'status':row.status}


class Parameters(BaseModel):
    width:int=Field(default=1024,ge=512,le=1536,multiple_of=512)
    height:int=Field(default=1024,ge=512,le=1536,multiple_of=512)
    style:str=Field(min_length=1,max_length=500)


class ExperimentRequest(BaseModel):
    panel_index:int=Field(ge=0)
    variants:list[Parameters]=Field(min_length=2,max_length=6)


class AdoptExperiment(BaseModel):
    expected_version:str | None = None


@router.post('/experiments/{task_id}/adopt')
async def adopt_experiment(task_id:str,payload:AdoptExperiment,db=Depends(get_db)):
    task=await db.get(Task,task_id)
    if not task or task.type!='experiment' or task.status.value!='completed':raise HTTPException(409,'实验候选尚未完成')
    data=(task.result or {}).get('experiment',{});chapter,tasks=await context(db,data['chapter_id'])
    from app.api.routes.editing import unlocked,latest_version,snapshot
    from app.models.orm import TaskStatus,Phase
    unlocked(tasks)
    version=await latest_version(db,chapter.id)
    if payload.expected_version!=(version.id if version else None):raise HTTPException(409,'章节版本已变化，请刷新后重试')
    panels=list((await db.execute(select(Panel).where(Panel.chapter_id==chapter.id).order_by(Panel.index))).scalars())
    target=next((p for p in panels if p.index==data['panel_index']),None)
    if not target or target.image_url!=data['snapshot']['source_url']:raise HTTPException(409,'源分镜已变化，不能覆盖新稿')
    if any(p.status.value!='passed' for p in panels):raise HTTPException(409,'请先完成全部分镜审核')
    state=deepcopy((tasks[0].result or {}).get('state',{})) if tasks else {}
    url=task.result['candidate_url'];new_panels=[{'index':p.index,'image_url':url if p==target else p.image_url,'status':'passed'} for p in panels]
    from app.agents.layout_artist import LayoutArtistAgent
    final=await LayoutArtistAgent().compose_final(new_panels,state.get('dialogues') or chapter.dialogues or {},effects=state.get('effects',{}))
    await snapshot(db,chapter,tasks,'采用实验候选前')
    target.image_url=url;target.review_result={'type':'user_adopted_experiment','experiment_task_id':task_id}
    state.update(panels=new_panels,final_comic=final,phase='completed',next_node='done',adopted_experiment=task_id)
    chapter.phase=Phase.COMPLETED
    for old in tasks:
        if old.status==TaskStatus.NEEDS_HUMAN:old.status=TaskStatus.FAILED;old.error_message='已由实验候选稿替代'
    published=Task(id=str(uuid4()),project_id=chapter.project_id,chapter_id=chapter.id,type='adopted_experiment',status=TaskStatus.COMPLETED,result={'state':state,'final_comic':final})
    db.add(published);await db.flush();await snapshot(db,chapter,[published],'采用实验候选');await db.commit()
    return final


@router.post('/chapters/{chapter_id}/experiments')
async def experiment(chapter_id:str,payload:ExperimentRequest,db=Depends(get_db)):
    chapter,tasks=await context(db,chapter_id)
    if settings.AI_PROVIDER!='chatgpt_desktop':raise HTTPException(422,'当前 HTTP 生图适配器不支持参考图实验；请先配置支持参考图的服务')
    source=(await db.execute(select(Panel).where(Panel.chapter_id==chapter_id,Panel.index==payload.panel_index))).scalar_one_or_none()
    if not source:raise HTTPException(404,'分镜不存在')
    state=deepcopy((tasks[0].result or {}).get('state',{})) if tasks else {}
    frozen={'panel':next((p for p in (chapter.storyboard or {}).get('panels',[]) if p['index']==payload.panel_index),{'index':payload.panel_index}),'characters':state.get('characters',[]),'source_url':source.image_url}
    items=[]
    for i,params in enumerate(payload.variants):
        item={'chapter_id':chapter_id,'panel_index':payload.panel_index,'parameters':params.model_dump(),'references':[source.image_url],'snapshot':frozen,
              'prompt':'在保持参考图人物身份、动作与场景的前提下生成参数实验候选，不覆盖原稿。设定：'+json.dumps(frozen,ensure_ascii=False)}
        items.append({'kind':'experiment','chapter_id':chapter_id,'status':'queued','label':f'方案 {i+1}','experiment':item})
    row=ProductionBatch(id=str(uuid4()),project_id=chapter.project_id,name=f'第{payload.panel_index+1}格参数实验',status='paused',items=items)
    db.add(row);await db.commit();return {'id':row.id}
