from copy import deepcopy
import hashlib
import json
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.db.session import get_db
from app.models.orm import CharacterProfile,CharacterAssetPolicy,CharacterAssetRevision,Task,ModelCall,Project,VisualReference,TaskStatus
from app.models.schemas import StoryboardSchema, DialogueSchema
from app.services.production_records import asset_hash
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



class VisualReferenceInput(BaseModel):
    kind: Literal['character', 'scene', 'prop']
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=1000)
    image_url: str = Field(min_length=1, max_length=300)


def reference_data(row):
    return {key: getattr(row, key) for key in ('id', 'kind', 'name', 'description', 'image_url', 'sha256')}


async def approved_reference_library(db, project_id):
    rows = (await db.execute(select(VisualReference).where(VisualReference.project_id == project_id))).scalars()
    return [reference_data(row) for row in rows if asset_hash(row.image_url) == row.sha256]


@router.get('/projects/{project_id}/visual-references')
async def list_visual_references(project_id: str, db=Depends(get_db)):
    rows = (await db.execute(select(VisualReference).where(VisualReference.project_id == project_id))).scalars()
    return [reference_data(row) for row in rows]


@router.post('/projects/{project_id}/visual-references', status_code=201)
async def lock_visual_reference(project_id: str, data: VisualReferenceInput, db=Depends(get_db)):
    if not await db.get(Project, project_id):
        raise HTTPException(404, '项目不存在')
    digest = asset_hash(data.image_url)
    if not digest:
        raise HTTPException(422, '请选择已上传或已生成的本机图片')
    row = VisualReference(id=uuid4().hex, project_id=project_id, sha256=digest, **data.model_dump())
    db.add(row)
    await db.commit()
    return reference_data(row)


class VisualReferencePrompt(BaseModel):
    kind: Literal['character', 'scene', 'prop']
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)


@router.post('/projects/{project_id}/visual-reference-candidate')
async def generate_visual_reference(project_id: str, data: VisualReferencePrompt, db=Depends(get_db)):
    if not await db.get(Project, project_id):
        raise HTTPException(404, '项目不存在')
    from app.tools.image_gen import ImageGeneratorClient
    from app.tools.desktop_bridge import stage_context
    token = stage_context.set('visual_reference')
    try:
        kind = {'character': '单一角色全身设定，清楚呈现服装和轮廓', 'scene': '无人场景建立镜头，清楚呈现空间关系', 'prop': '单件道具设定，清楚呈现形状材质'}[data.kind]
        url = await ImageGeneratorClient().generate_image(f'漫画视觉参考图。{kind}。名称：{data.name}。设定：{data.description}。')
    except Exception as error:
        raise HTTPException(502, str(error) if isinstance(error, ValueError) else '参考图生成失败，请检查模型连接') from error
    finally:
        stage_context.reset(token)
    return {'image_url': url}


async def resolve_visual_bindings(db, project_id, bindings, indices):
    if set(bindings) - {str(index) for index in indices}:
        raise HTTPException(422, '参考图绑定超出所选分镜范围')
    result = {}
    for index, ids in bindings.items():
        if len(ids) > 3 or len(ids) != len(set(ids)):
            raise HTTPException(422, '每格最多选三张不同参考图')
        result[index] = []
        for asset_id in ids:
            row = await db.get(VisualReference, asset_id)
            if not row or row.project_id != project_id or asset_hash(row.image_url) != row.sha256:
                raise HTTPException(422, '参考版本不可用或不属于此项目')
            result[index].append(reference_data(row))
    return result


@router.get('/chapters/{chapter_id}/shot-plan')
async def shot_plan(chapter_id: str, db=Depends(get_db)):
    from app.api.routes.editing import context, latest_version
    chapter, tasks = await context(db, chapter_id)
    version = await latest_version(db, chapter_id)
    task = tasks[0] if tasks else None
    result = (task.result or {}) if task else {}
    state = result.get('state', {})
    from app.services.comic_plan import effective_references
    board = state.get('storyboard') or chapter.storyboard
    inherited = effective_references(board, state.get('scene_reference_library', []), {}) if board else {}
    return {'task_id': task.id if task else None, 'revision': result.get('plan_revision'),
            'expected_version': version.id if version else None,
            'waiting': result.get('waiting_for') == 'storyboard_review' and task.status == TaskStatus.NEEDS_HUMAN,
            'storyboard': state.get('storyboard') or chapter.storyboard,
            'previous_novel_context': state.get('previous_novel_context'),
            'dialogues': state.get('dialogues') or chapter.dialogues,
            'bindings': {k: [a['id'] for a in v] for k, v in state.get('visual_reference_bindings', {}).items()},
            'overrides': list(state.get('visual_reference_overrides', state.get('visual_reference_bindings', {}) if not state.get('scene_reference_library') else {})),
            'inherited': {k: [a['id'] for a in v] for k, v in inherited.items()},
            'dependencies': {str(panel['index']): panel.get('continuity_source_indices', []) for panel in state.get('panels', [])}}


class ShotPlanEdit(BaseModel):
    task_id: str
    expected_revision: str | None = None
    storyboard: StoryboardSchema
    dialogues: DialogueSchema | None = None
    bindings: dict[str, list[str]] = Field(default_factory=dict, max_length=24)


@router.put('/chapters/{chapter_id}/shot-plan')
async def save_shot_plan(chapter_id: str, data: ShotPlanEdit, db=Depends(get_db)):
    from app.api.routes.editing import context, unlocked, snapshot
    from sqlalchemy import update
    chapter, tasks = await context(db, chapter_id)
    unlocked(tasks)
    task = tasks[0] if tasks else None
    old = (task.result or {}) if task else {}
    if not task or task.id != data.task_id or task.status != TaskStatus.NEEDS_HUMAN or old.get('waiting_for') != 'storyboard_review' or old.get('plan_revision') != data.expected_revision:
        raise HTTPException(409, '分镜草图已变化，请刷新后编辑')
    state = deepcopy(old['state'])
    board = data.storyboard.model_dump()
    if [p['index'] for p in board['panels']] != [p['index'] for p in state['storyboard']['panels']]:
        raise HTTPException(422, '草图调整须保留当前分镜索引与数量')
    for panel in board['panels']:
        subshots = panel['composition'].get('subshots') or []
        if not isinstance(subshots, list) or len(subshots) > 4:
            raise HTTPException(422, '每格最多四个子镜头')
        for shot in subshots:
            region = shot.get('region') if isinstance(shot, dict) else None
            if not isinstance(region, dict):
                raise HTTPException(422, '子镜头需要填写位置和大小')
            x, y, width, height = (region.get(key) for key in ('x', 'y', 'width', 'height'))
            if not all(type(value) in (int, float) and 0 <= value <= 100 for value in (x, y, width, height)) or not width or not height or x + width > 100 or y + height > 100:
                raise HTTPException(422, '子镜头须位于画框内，且宽高大于零')
    from app.services.comic_plan import effective_references, validate_pages, validate_scenes
    indices = {panel['index'] for panel in board['panels']}
    try:
        validate_scenes(board)
        if board.get('pages') is not None:
            validate_pages(board['pages'], indices)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    overrides = await resolve_visual_bindings(db, chapter.project_id, data.bindings, indices)
    library = await approved_reference_library(db, chapter.project_id)
    state['scene_reference_library'] = library
    state['visual_reference_overrides'] = overrides
    state['visual_reference_bindings'] = effective_references(board, library, overrides)
    if data.dialogues is not None:
        indices = {panel['index'] for panel in board['panels']}
        if any(bubble.panel_index not in indices or len(bubble.text) > 60 for bubble in data.dialogues.bubbles):
            raise HTTPException(422, '对白须引用已有分镜且每条不超过60字')
        state['dialogues'] = data.dialogues.model_dump()
    state['storyboard'] = board
    revision = uuid4().hex
    await snapshot(db, chapter, tasks, '分镜草图确认前')
    changed = await db.execute(update(Task).where(Task.id == task.id, Task.status == TaskStatus.NEEDS_HUMAN,
        Task.updated_at == task.updated_at).values(result={**old, 'state': state, 'plan_revision': revision}))
    if changed.rowcount != 1:
        raise HTTPException(409, '分镜草图已变化，请刷新后编辑')
    await db.commit()
    return {'revision': revision}
