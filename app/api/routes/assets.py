from copy import deepcopy
import hashlib
import json
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.db.session import get_db
from app.models.orm import CharacterProfile,CharacterAssetPolicy,CharacterAssetRevision,Task,ModelCall
from app.services.character_details import modules
from app.tools.media import local_image_path

router=APIRouter()


async def profile_for(db,project_id,character_id):
    profile=await db.get(CharacterProfile,character_id)
    if not profile or profile.project_id!=project_id:raise HTTPException(404,'角色不存在')
    return profile


class AssetChange(BaseModel):
    expected_revision: str | None = None


@router.get('/projects/{project_id}/characters/{character_id}/assets')
async def assets(project_id:str,character_id:str,db=Depends(get_db)):
    await profile_for(db,project_id,character_id)
    policy=await db.get(CharacterAssetPolicy,character_id)
    rows=(await db.execute(select(CharacterAssetRevision).where(CharacterAssetRevision.character_id==character_id).order_by(CharacterAssetRevision.created_at.desc()))).scalars()
    return {'revision_id':policy.revision_id if policy else None,'locked':policy.locked if policy else False,
            'revisions':[{'id':r.id,'sha256':r.sha256,'snapshot':r.snapshot,'created_at':r.created_at} for r in rows]}


@router.post('/projects/{project_id}/characters/{character_id}/approve')
async def approve(project_id:str,character_id:str,data:AssetChange,db=Depends(get_db)):
    profile=await profile_for(db,project_id,character_id)
    policy=await db.get(CharacterAssetPolicy,character_id)
    if data.expected_revision!=(policy.revision_id if policy else None):raise HTTPException(409,'角色版本已变化，请刷新')
    if policy and policy.locked:raise HTTPException(409,'已锁定，请先解锁再审批新版本')
    try:
        reference=local_image_path(profile.reference_image_url or '')
        reference_hash=hashlib.sha256(reference.read_bytes()).hexdigest()
    except (ValueError,OSError):raise HTTPException(422,'审批前请上传有效角色参考图')
    draft={'name':profile.name,'reference_image_url':profile.reference_image_url,'reference_sha256':reference_hash,'modules':await modules(db,profile)}
    digest=hashlib.sha256(json.dumps(draft,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    row=CharacterAssetRevision(id=uuid4().hex,character_id=character_id,snapshot=deepcopy(draft),sha256=digest)
    db.add(row)
    if not policy:
        policy=CharacterAssetPolicy(character_id=character_id,revision_id=row.id,locked=True);db.add(policy)
    else:policy.revision_id=row.id;policy.locked=True
    await db.commit()
    return {'revision_id':row.id,'sha256':digest,'locked':True,'message':'新生成或显式图片修订使用此审批版；已有图像不自动改变。'}


@router.post('/projects/{project_id}/characters/{character_id}/unlock')
async def unlock(project_id:str,character_id:str,data:AssetChange,db=Depends(get_db)):
    await profile_for(db,project_id,character_id)
    policy=await db.get(CharacterAssetPolicy,character_id)
    if not policy or policy.revision_id!=data.expected_revision:raise HTTPException(409,'审批版本已变化或不存在')
    policy.locked=False;await db.commit()
    return {'locked':False,'message':'可编辑草稿。生成仍使用旧审批版，直到重新审批。'}


@router.get('/chapters/{chapter_id}/evidence')
async def evidence(chapter_id:str,db=Depends(get_db)):
    from app.api.routes.editing import context
    chapter,tasks=await context(db,chapter_id)
    ids=[t.id for t in tasks]
    calls=list((await db.execute(select(ModelCall).where(ModelCall.task_id.in_(ids)).order_by(ModelCall.created_at))).scalars()) if ids else []
    state=(tasks[0].result or {}).get('state',{}) if tasks else {}
    return {'knowledge_evidence':state.get('knowledge_evidence',[]),'character_revisions':[{'name':c.get('name'),'revision_id':c.get('asset_revision_id'),'sha256':c.get('asset_sha256')} for c in state.get('characters',[])],
            'calls':[{'id':r.id,'task_id':r.task_id,'kind':r.kind,'model':r.model,'stage':r.stage,'status':r.status,'usage':r.usage} for r in calls],
            'currency_cost':None,'note':'仅列出当前章节任务的持久 API 预留；原有历史调用未知，实验任务可按其 task_id 查调用记录。'}
