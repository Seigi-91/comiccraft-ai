from copy import deepcopy
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core.config import settings
from app.db.session import get_db, AsyncSessionLocal
from app.models.orm import PanelRepair, Panel, PanelStatus, Task, TaskStatus, Phase
from app.models.schemas import BubblePosition
from app.api.routes.editing import context, unlocked, snapshot, latest_version
from app.services.inpainting import create_mask, edit_image
from uuid import uuid4

router=APIRouter()


@router.get('/config')
async def config():
    return {'configured':settings.IMAGE_EDIT_PROVIDER == 'codex_cli' or (settings.IMAGE_EDIT_PROVIDER == 'openai' and bool(settings.IMAGE_EDIT_BASE_URL)),'provider':settings.IMAGE_EDIT_PROVIDER,'model':settings.IMAGE_EDIT_MODEL,
            'note':'仅配置状态，不代表服务已通过真实生图验证。未选区域由原图像素合成保护。'}


class RepairRequest(BaseModel):
    instructions: str = Field(min_length=1,max_length=4000)
    source_url: str
    polygons: list[list[BubblePosition]] = Field(min_length=1,max_length=30)


async def run_repair(repair_id):
    async with AsyncSessionLocal() as db:
        row=await db.get(PanelRepair,repair_id)
        try:
            row.candidate_url=await edit_image(row.source_url,row.mask_url,row.instructions)
            row.status='ready'
        except Exception as error:
            row.status='failed'
            row.error=str(error) if isinstance(error,ValueError) else '编辑服务连接或解码失败，请检查服务后重试'
        await db.commit()


@router.post('/{chapter_id}/panels/{panel_index}')
async def create(chapter_id: str,panel_index:int,payload:RepairRequest,background_tasks:BackgroundTasks,db=Depends(get_db)):
    chapter,tasks=await context(db,chapter_id);unlocked(tasks)
    if settings.IMAGE_EDIT_PROVIDER == 'chatgpt_desktop':
        raise HTTPException(503,'人工精修回填已停用，请在设置中配置并验证自动图像编辑连接')
    if settings.IMAGE_EDIT_PROVIDER not in {'chatgpt_desktop','codex_cli'} and not settings.IMAGE_EDIT_BASE_URL:
        raise HTTPException(503,'尚未配置图像编辑服务，请配置 IMAGE_EDIT_BASE_URL / IMAGE_EDIT_MODEL / IMAGE_EDIT_API_KEY')
    state = (tasks[0].result or {}).get('state', {}) if tasks else {}
    draft_panels = state.get('panels') or []
    if draft_panels:
        draft = next((panel for panel in draft_panels if panel['index'] == panel_index), None)
        source_url = draft.get('image_url') if draft else None
    else:
        panel = (await db.execute(select(Panel).where(Panel.chapter_id == chapter_id, Panel.index == panel_index))).scalar_one_or_none()
        source_url = panel.image_url if panel else None
    if not source_url or source_url != payload.source_url:
        raise HTTPException(409, '原图已变化，请重新打开精修器')
    if any(not 3<=len(p)<=2000 for p in payload.polygons):
        raise HTTPException(422,'每个选区需3–2000个点')
    try: mask_url=create_mask(source_url,[[p.model_dump() for p in poly] for poly in payload.polygons])
    except ValueError as error:raise HTTPException(422,str(error))
    row=PanelRepair(id=str(uuid4()),chapter_id=chapter_id,panel_index=panel_index,source_url=source_url,mask_url=mask_url,instructions=payload.instructions,status='pending')
    db.add(row);await db.commit()
    background_tasks.add_task(run_repair,row.id)
    return {'id':row.id}


@router.get('/{chapter_id}')
async def list_repairs(chapter_id:str,db=Depends(get_db)):
    await context(db,chapter_id)
    rows=(await db.execute(select(PanelRepair).where(PanelRepair.chapter_id==chapter_id).order_by(PanelRepair.created_at.desc()).limit(100))).scalars()
    from app.tools.desktop_bridge import read_job
    return [{'job':read_job(r.job_id) if r.job_id else None,'id':r.id,'panel_index':r.panel_index,'source_url':r.source_url,'mask_url':r.mask_url,'candidate_url':r.candidate_url,'instructions':r.instructions,'status':r.status,'error':r.error} for r in rows]


class Accept(BaseModel):
    expected_version: str | None = None


@router.post('/{chapter_id}/{repair_id}/accept')
async def accept(chapter_id:str,repair_id:str,payload:Accept,db=Depends(get_db)):
    chapter,tasks=await context(db,chapter_id);unlocked(tasks)
    row=await db.get(PanelRepair,repair_id)
    if not row or row.chapter_id!=chapter_id or row.status!='ready':raise HTTPException(409,'候选稿不存在或尚不可采用')
    version=await latest_version(db,chapter_id)
    if payload.expected_version!=(version.id if version else None):raise HTTPException(409,'章节已变化，请刷新后再确认')
    panels=list((await db.execute(select(Panel).where(Panel.chapter_id==chapter_id).order_by(Panel.index))).scalars())
    panel=next((p for p in panels if p.index==row.panel_index),None)
    if not panel or panel.image_url!=row.source_url:raise HTTPException(409,'原图已变化，此候选不能覆盖新稿')
    if any(p.status!=PanelStatus.PASSED for p in panels):raise HTTPException(409,'请先完成所有分镜审核')
    state=deepcopy((tasks[0].result or {}).get('state',{})) if tasks else {}
    new_panels=[{'index':p.index,'image_url':row.candidate_url if p==panel else p.image_url,'status':'passed'} for p in panels]
    from app.agents.layout_artist import LayoutArtistAgent
    try: final=await LayoutArtistAgent().compose_final(new_panels,state.get('dialogues') or chapter.dialogues or {},effects=state.get('effects',{}))
    except ValueError as error:raise HTTPException(422,str(error))
    await snapshot(db,chapter,tasks,'采用局部精修前')
    panel.image_url=row.candidate_url;panel.review_result={'type':'human_accepted_local_repair','repair_id':row.id,'note':'用户比较后采用；未声称模型自动审核通过'}
    state.update(panels=new_panels,final_comic=final,phase='completed',next_node='done')
    state['local_repair']={'id':row.id,'mask_url':row.mask_url,'source_url':row.source_url,'instructions':row.instructions}
    task=Task(id=str(uuid4()),project_id=chapter.project_id,chapter_id=chapter_id,type='local_repair',status=TaskStatus.COMPLETED,result={'state':state,'final_comic':final})
    db.add(task);row.status='accepted';chapter.phase=Phase.COMPLETED
    for old in tasks:
        if old.status==TaskStatus.NEEDS_HUMAN:old.status=TaskStatus.FAILED;old.error_message='已由局部精修稿替代'
    await db.flush();await snapshot(db,chapter,[task],'局部精修：'+row.instructions[:60]);await db.commit()
    return final


class RepairReply(BaseModel):
    image_url: str
    allow_resize: bool = False


@router.post('/{chapter_id}/{repair_id}/reply')
async def repair_reply(chapter_id:str,repair_id:str,payload:RepairReply,db=Depends(get_db)):
    row=await db.get(PanelRepair,repair_id)
    if not row or row.chapter_id!=chapter_id or row.status!='waiting':raise HTTPException(409,'待办已失效')
    from app.tools.media import local_image_path
    from app.services.inpainting import composite_candidate
    try:
        row.candidate_url=composite_candidate(row.source_url,row.mask_url,local_image_path(payload.image_url).read_bytes(),allow_resize=payload.allow_resize)
    except (ValueError,OSError) as error:raise HTTPException(422,str(error))
    if row.job_id:
        from app.tools.desktop_bridge import read_job, save_job
        job=read_job(row.job_id);job.update(status='completed',response=row.candidate_url);save_job(job)
    row.status='ready';await db.commit()
    return {'candidate_url':row.candidate_url}
