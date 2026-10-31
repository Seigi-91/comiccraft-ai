"""Transactional chapter editing and immutable, restorable snapshots."""
from copy import deepcopy
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select, delete, update
from app.db.session import get_db
from app.models.orm import Chapter, ChapterVersion, Panel, Task, TaskStatus, Phase, PanelStatus
from app.models.schemas import StorySchema, StoryboardSchema, DialogueSchema
from app.api.routes.tasks import active_tasks, run_generation

router = APIRouter()


async def context(db, chapter_id):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "章节不存在")
    tasks = list((await db.execute(select(Task).where(Task.chapter_id == chapter_id).order_by(Task.created_at.desc()))).scalars())
    return chapter, tasks


def unlocked(tasks):
    if any(t.id in active_tasks or t.status in (TaskStatus.RUNNING, TaskStatus.PENDING) for t in tasks):
        raise HTTPException(409, "任务执行中，请等待当前阶段完成后编辑")


async def snapshot(db, chapter, tasks, label):
    panels = list((await db.execute(select(Panel).where(Panel.chapter_id == chapter.id).order_by(Panel.index))).scalars())
    latest = tasks[0] if tasks else None
    state = deepcopy((latest.result or {}).get("state", {})) if latest else {}
    data = {key: deepcopy(state.get(key) or getattr(chapter, key)) for key in ("outline", "storyboard", "dialogues")}
    data.update(title=chapter.title, phase=chapter.phase.value,
                panels=[{"index": p.index, "image_url": p.image_url, "status": p.status.value, "review_result": p.review_result} for p in panels],
                task_result=deepcopy(latest.result) if latest else None)
    version = ChapterVersion(id=str(uuid4()), chapter_id=chapter.id, label=label, snapshot=data)
    db.add(version)
    return version


class Edit(BaseModel):
    section: Literal["outline", "storyboard", "dialogues"]
    content: dict
    expected_version: str | None = None


async def latest_version(db, chapter_id):
    return (await db.execute(select(ChapterVersion).where(ChapterVersion.chapter_id == chapter_id).order_by(ChapterVersion.created_at.desc(), ChapterVersion.id.desc()).limit(1))).scalar_one_or_none()


@router.get("/{chapter_id}/versions")
async def versions(chapter_id: str, db=Depends(get_db)):
    await context(db, chapter_id)
    rows = (await db.execute(select(ChapterVersion).where(ChapterVersion.chapter_id == chapter_id).order_by(ChapterVersion.created_at.desc(), ChapterVersion.id.desc()))).scalars()
    return [{"id": v.id, "label": v.label, "created_at": v.created_at, "snapshot": v.snapshot} for v in rows]


@router.put("/{chapter_id}/content")
async def edit(chapter_id: str, payload: Edit, db=Depends(get_db)):
    chapter, tasks = await context(db, chapter_id)
    unlocked(tasks)
    latest = await latest_version(db, chapter_id)
    if (latest.id if latest else None) != payload.expected_version:
        raise HTTPException(409, "版本已变化，请刷新后重新编辑")
    try:
        content = {"outline": StorySchema, "storyboard": StoryboardSchema, "dialogues": DialogueSchema}[payload.section].model_validate(payload.content).model_dump()
    except ValidationError as e:
        raise HTTPException(422, str(e))
    state = deepcopy((tasks[0].result or {}).get("state", {})) if tasks else {}
    state.update(project_id=chapter.project_id, current_chapter=chapter_id)
    if payload.section == "storyboard" and not (state.get("outline") or chapter.outline):
        raise HTTPException(422, "请先保存剧情大纲")
    if payload.section == "storyboard":
        panels = content["panels"]
        if not 1 <= len(panels) <= 24 or [p["index"] for p in panels] != list(range(len(panels))):
            raise HTTPException(422, "分镜必须为 1–24 格，索引连续")
    if payload.section == "dialogues":
        board = state.get("storyboard") or chapter.storyboard
        valid = {p["index"] for p in (board or {}).get("panels", [])}
        if not valid or any(b["panel_index"] not in valid or len(b["text"]) > 60 for b in content["bubbles"]):
            raise HTTPException(422, "台词必须引用已有分镜，每条不超过 60 字")
    await snapshot(db, chapter, tasks, "编辑前自动保存")
    for key in ("outline", "storyboard", "dialogues"):
        if state.get(key):
            setattr(chapter, key, state[key])
    setattr(chapter, payload.section, content)
    state[payload.section] = content
    downstream = {"outline": ["storyboard", "dialogues"], "storyboard": ["dialogues"], "dialogues": []}[payload.section]
    for key in downstream:
        setattr(chapter, key, None)
        state.pop(key, None)
    for key in ("final_comic", "review_history", "events", "effects"):
        state.pop(key, None)
    state.update(panels=[], retry_count=0, human_intervene=False)
    state["next_node"] = {"outline": "generate_storyboard", "storyboard": "generate_dialogue", "dialogues": "arbitrate_conflicts"}[payload.section]
    if payload.section == "outline":
        existing = {c["name"]: c for c in state.get("characters", [])}
        state["characters"] = [{**existing.get(c.get("name"), {}), **c} for c in content["characters"]]
    chapter.phase = Phase.STORYBOARDING if payload.section == "outline" else Phase.DIALOGUE if payload.section == "storyboard" else Phase.PANEL_GENERATION
    state["phase"] = chapter.phase.value
    await db.execute(delete(Panel).where(Panel.chapter_id == chapter_id))
    # A new task prevents completed ChatGPT job caches from replaying stale results.
    for task in tasks:
        if task.status == TaskStatus.NEEDS_HUMAN:
            task.status = TaskStatus.FAILED
            task.error_message = "已由新的编辑稿替代"
    task = Task(id=str(uuid4()), project_id=chapter.project_id, chapter_id=chapter_id, type="edited_chapter", status=TaskStatus.NEEDS_HUMAN, result={"state": state})
    db.add(task)
    await db.flush()
    await snapshot(db, chapter, [task], "保存" + {"outline": "大纲", "storyboard": "分镜", "dialogues": "台词"}[payload.section])
    await db.commit()
    return {"status": "saved", "task_id": task.id, "message": "已保存。下游内容需重新生成，可从当前编辑稿继续。"}


class Restore(BaseModel):
    expected_version: str | None = None


@router.post("/{chapter_id}/versions/{version_id}/restore")
async def restore(chapter_id: str, version_id: str, payload: Restore, db=Depends(get_db)):
    chapter, tasks = await context(db, chapter_id)
    unlocked(tasks)
    latest = await latest_version(db, chapter_id)
    if (latest.id if latest else None) != payload.expected_version:
        raise HTTPException(409, "版本已变化，请刷新后重试")
    version = await db.get(ChapterVersion, version_id)
    if not version or version.chapter_id != chapter_id:
        raise HTTPException(404, "版本不存在")
    await snapshot(db, chapter, tasks, "回退前自动保存")
    data = deepcopy(version.snapshot)
    for key in ("title", "outline", "storyboard", "dialogues"):
        setattr(chapter, key, data.get(key))
    chapter.phase = Phase(data["phase"])
    await db.execute(delete(Panel).where(Panel.chapter_id == chapter_id))
    for panel in data["panels"]:
        db.add(Panel(id=str(uuid4()), chapter_id=chapter_id, **panel))
    for t in tasks:
        if t.status == TaskStatus.NEEDS_HUMAN:
            t.status = TaskStatus.FAILED
            t.error_message = "已由回退版本替代"
    result = data.get("task_result") or {"state": {}}
    result = {"state": result.get("state", {}), **({"final_comic": result["final_comic"]} if result.get("final_comic") else {})}
    # Restore artifacts, never reactivate an old pending handoff.
    status = TaskStatus.COMPLETED if chapter.phase == Phase.COMPLETED else TaskStatus.NEEDS_HUMAN
    task = Task(id=str(uuid4()), project_id=chapter.project_id, chapter_id=chapter_id, type="restored_chapter", status=status, result=result)
    if status != TaskStatus.COMPLETED:
        result["state"]["next_node"] = "generate_panels" if chapter.dialogues else "generate_dialogue" if chapter.storyboard else "generate_storyboard" if chapter.outline else "generate_outline"
    db.add(task)
    await db.flush()
    await snapshot(db, chapter, [task], "回退到：" + version.label)
    await db.commit()
    return {"status": "restored"}


class Revise(BaseModel):
    instructions: str = Field(min_length=1, max_length=4000)


class BubbleEdit(BaseModel):
    dialogues: DialogueSchema
    expected_version: str | None = None


@router.post("/{chapter_id}/auto-place-bubbles")
async def auto_place(chapter_id: str, background_tasks: BackgroundTasks, db=Depends(get_db)):
    chapter, tasks = await context(db, chapter_id)
    unlocked(tasks)
    rows = list((await db.execute(select(Panel).where(Panel.chapter_id == chapter_id).order_by(Panel.index))).scalars())
    if not rows or any(p.status != PanelStatus.PASSED for p in rows):
        raise HTTPException(409, "请先完成全部分镜审核")
    state = deepcopy((tasks[0].result or {}).get("state", {})) if tasks else {}
    state['dialogues'] = state.get('dialogues') or chapter.dialogues or {'bubbles': []}
    if not state['dialogues']['bubbles']:
        raise HTTPException(422, "请先添加台词")
    await snapshot(db, chapter, tasks, "AI 气泡定位前")
    state.update(panels=[{"index":p.index,"image_url":p.image_url,"status":p.status.value} for p in rows],next_node="auto_place_bubbles",phase="layout")
    task = Task(id=str(uuid4()), project_id=chapter.project_id, chapter_id=chapter_id, type="bubble_placement", status=TaskStatus.PENDING, result={"state":state})
    for old in tasks:
        if old.status == TaskStatus.NEEDS_HUMAN:
            old.status=TaskStatus.FAILED
            old.error_message="已由 AI 排版任务替代"
    db.add(task)
    await db.commit()
    background_tasks.add_task(run_generation, chapter.project_id, chapter_id, task.id)
    return {"task_id":task.id}


@router.get("/{chapter_id}/bubble-layout")
async def bubble_layout(chapter_id: str, db=Depends(get_db)):
    chapter, tasks = await context(db, chapter_id)
    state = (tasks[0].result or {}).get("state", {}) if tasks else {}
    rows = list((await db.execute(select(Panel).where(Panel.chapter_id == chapter_id).order_by(Panel.index))).scalars())
    panels = [{"index": p.index, "image_url": p.image_url, "status": p.status.value} for p in rows]
    if not panels or any(p["status"] != "passed" for p in panels):
        raise HTTPException(409, "请先完成分镜审核")
    from app.agents.layout_artist import LayoutArtistAgent
    try:
        rendered = await LayoutArtistAgent().compose_final(panels, state.get("dialogues") or chapter.dialogues or {}, effects=state.get("effects", {}))
    except ValueError as e:
        raise HTTPException(422, str(e))
    version = await latest_version(db, chapter_id)
    return {"panels": panels, "dialogues": {"bubbles": rendered["bubble_geometry"]}, "expected_version": version.id if version else None}


@router.put("/{chapter_id}/bubble-layout")
async def save_bubble_layout(chapter_id: str, payload: BubbleEdit, db=Depends(get_db)):
    chapter, tasks = await context(db, chapter_id)
    unlocked(tasks)
    version = await latest_version(db, chapter_id)
    if payload.expected_version != (version.id if version else None):
        raise HTTPException(409, "作品版本已变化，请重新打开气泡编辑器")
    rows = list((await db.execute(select(Panel).where(Panel.chapter_id == chapter_id).order_by(Panel.index))).scalars())
    valid = {p.index for p in rows}
    if any(b.panel_index not in valid or len(b.text)>60 for b in payload.dialogues.bubbles):
        raise HTTPException(422, "台词引用无效或超过 60 字")
    # Render first: invalid layouts never change the saved dialogue or published art.
    final = await compose_chapter(chapter_id, db, payload.dialogues.model_dump())
    return final


@router.post("/{chapter_id}/recompose")
async def recompose(chapter_id: str, db=Depends(get_db)):
    return await compose_chapter(chapter_id, db)


async def compose_chapter(chapter_id, db, replacement=None, effects=None):
    chapter, tasks = await context(db, chapter_id)
    unlocked(tasks)
    state = deepcopy((tasks[0].result or {}).get("state", {})) if tasks else {}
    rows = list((await db.execute(select(Panel).where(Panel.chapter_id == chapter_id).order_by(Panel.index))).scalars())
    if not rows or any(p.status != PanelStatus.PASSED for p in rows):
        raise HTTPException(409, "需要全部通过审核的分镜才能重新排版")
    from app.agents.layout_artist import LayoutArtistAgent
    panels = [{"index": p.index, "image_url": p.image_url, "status": p.status.value} for p in rows]
    try:
        final = await LayoutArtistAgent().compose_final(panels, replacement if replacement is not None else state.get("dialogues") or chapter.dialogues or {}, effects=effects if effects is not None else state.get("effects", {}))
    except ValueError as error:
        raise HTTPException(422, str(error))
    await snapshot(db, chapter, tasks, "特效修改前" if effects is not None else "漫画气泡排版前")
    if effects is not None:
        state["effects"] = effects
    if replacement is not None:
        state["dialogues"] = replacement
        chapter.dialogues = replacement
    state.update(panels=panels, final_comic=final, phase="completed", next_node="done")
    chapter.phase = Phase.COMPLETED
    for previous in tasks:
        if previous.status == TaskStatus.NEEDS_HUMAN:
            previous.status = TaskStatus.FAILED
            previous.error_message = "已由气泡排版稿替代"
    task = Task(id=str(uuid4()), project_id=chapter.project_id, chapter_id=chapter_id, type="bubble_layout", status=TaskStatus.COMPLETED, result={"state": state, "final_comic": final})
    db.add(task)
    await db.flush()
    await snapshot(db, chapter, [task], "特效合成" if effects is not None else "漫画气泡排版")
    await db.commit()
    return final


@router.post("/{chapter_id}/panels/{panel_index}/revise")
async def revise(chapter_id: str, panel_index: int, payload: Revise, background_tasks: BackgroundTasks, db=Depends(get_db)):
    chapter, tasks = await context(db, chapter_id)
    unlocked(tasks)
    state = deepcopy((tasks[0].result or {}).get("state", {})) if tasks else {}
    board = state.get("storyboard") or chapter.storyboard
    panels = list((await db.execute(select(Panel).where(Panel.chapter_id == chapter_id).order_by(Panel.index))).scalars())
    if not board or panel_index not in {p.index for p in panels}:
        raise HTTPException(422, "该分镜尚无可修订图片或分镜脚本")
    await snapshot(db, chapter, tasks, f"修订第 {panel_index + 1} 格前")
    state.update(storyboard=board, dialogues=state.get("dialogues") or chapter.dialogues,
                 outline=state.get("outline") or chapter.outline,
                 panels=[{"index": p.index, "image_url": p.image_url, "status": p.status.value} for p in panels],
                 next_node="generate_panels", phase="panel_generation", retry_count=0, human_intervene=False,
                 review_history=[{"panel_reviews": [{"panel_index": p.index, "passed": p.index != panel_index, "issues": [] if p.index != panel_index else [{"type": "人工修订", "severity": "medium", "description": payload.instructions, "suggestion": payload.instructions}]} for p in panels]}])
    from app.db.repositories import CharacterProfileRepository
    from app.services.character_details import creative_character
    profiles = await CharacterProfileRepository(db).list(chapter.project_id)
    current = {p.name: await creative_character(db, p) for p in profiles}
    state["characters"] = [{**c, **current.pop(c.get("name"), {})} for c in state.get("characters", [])] + list(current.values())
    state.pop("final_comic", None)
    task = Task(id=str(uuid4()), project_id=chapter.project_id, chapter_id=chapter_id, type="panel_revision", status=TaskStatus.PENDING, result={"state": state})
    for t in tasks:
        if t.status == TaskStatus.NEEDS_HUMAN:
            t.status = TaskStatus.FAILED
            t.error_message = "已由图片修订替代"
    db.add(task)
    await db.commit()
    background_tasks.add_task(run_generation, chapter.project_id, chapter_id, task.id)
    return {"status": "accepted", "task_id": task.id}
