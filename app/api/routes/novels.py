"""Novel import is local persistence only; model work uses the existing graph."""
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.models.orm import Project, Chapter, Phase, NovelDocument, NovelAdaptation
from app.services.novel_adaptation import normalize, split_novel, source_hash, chapter_source

router = APIRouter()


class ImportNovel(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=300000)


class Adapt(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    mode: Literal["faithful", "balanced", "free"] = "faithful"
    panel_count: int = Field(default=6, ge=1, le=24)
    notes: str = Field(default="", max_length=4000)
    required_facts: str = Field(default="", max_length=4000)


async def project(db, project_id):
    if not await db.get(Project, project_id):
        raise HTTPException(404, "项目不存在")


def summary(row):
    return {"id": row.id, "title": row.title, "sha256": row.sha256, "characters": len(row.text), "segments": row.segments, "created_at": row.created_at}


async def document(db, project_id, document_id):
    await project(db, project_id)
    row = await db.get(NovelDocument, document_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "原著不属于该项目")
    return row


@router.post("/preview")
async def preview(data: ImportNovel):
    try:
        text, segments = split_novel(data.text)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"title": data.title.strip(), "text": text, "segments": segments, "model_calls": 0}


@router.post("/preview-file")
async def preview_file(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith((".txt", ".md")):
        raise HTTPException(422, "目前支持 TXT / Markdown；PDF、EPUB 请先导出纯文本")
    raw = await file.read(2_000_001)
    if len(raw) > 2_000_000:
        raise HTTPException(413, "文件最多2MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gb18030")
        except UnicodeDecodeError:
            raise HTTPException(422, "无法解码，请保存为 UTF-8 文本")
    try:
        text, segments = split_novel(text)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"title": (file.filename or "小说").rsplit(".", 1)[0][:200], "text": text, "segments": segments, "model_calls": 0}


@router.get("/projects/{project_id}")
async def listing(project_id: str, db=Depends(get_db)):
    await project(db, project_id)
    rows = (await db.execute(select(NovelDocument).where(NovelDocument.project_id == project_id).order_by(NovelDocument.created_at.desc()))).scalars()
    return [summary(row) for row in rows]


@router.post("/projects/{project_id}")
async def import_novel(project_id: str, data: ImportNovel, db=Depends(get_db)):
    await project(db, project_id)
    if not data.title.strip():
        raise HTTPException(422, "请输入小说标题")
    try:
        text, segments = split_novel(data.text)
    except ValueError as e:
        raise HTTPException(422, str(e))
    row = NovelDocument(id=str(uuid4()), project_id=project_id, title=data.title.strip(), text=text, sha256=source_hash(text), segments=segments)
    db.add(row)
    await db.commit()
    return {**summary(row), "model_calls": 0}


@router.get("/projects/{project_id}/{document_id}")
async def get_document(project_id: str, document_id: str, db=Depends(get_db)):
    row = await document(db, project_id, document_id)
    adapted = (await db.execute(select(NovelAdaptation).where(NovelAdaptation.document_id == document_id))).scalars()
    return {**summary(row), "text": row.text, "adaptations": [{"segment_index": a.segment_index, "chapter_id": a.chapter_id, "settings": a.snapshot["settings"]} for a in adapted]}


@router.post("/projects/{project_id}/{document_id}/segments/{index}/adapt")
async def adapt(project_id: str, document_id: str, index: int, data: Adapt, db=Depends(get_db)):
    row = await document(db, project_id, document_id)
    if index < 0 or index >= len(row.segments):
        raise HTTPException(404, "片段不存在")
    if not data.title.strip():
        raise HTTPException(422, "请输入漫画章节标题")
    query = select(NovelAdaptation).where(NovelAdaptation.document_id == document_id, NovelAdaptation.segment_index == index)
    existing = (await db.execute(query)).scalar_one_or_none()
    if existing:
        return {"chapter_id": existing.chapter_id, "reused": True, "model_calls": 0}
    segment = row.segments[index]
    excerpt = row.text[segment["start"]:segment["end"]]
    snapshot = {"document_id": row.id, "document_title": row.title, "document_sha256": row.sha256, "segment": segment, "source_text": excerpt, "source_sha256": source_hash(excerpt), "settings": data.model_dump()}
    chapter = Chapter(id=str(uuid4()), project_id=project_id, title=data.title.strip(), phase=Phase.PLANNING)
    db.add(chapter)
    await db.flush()
    db.add(NovelAdaptation(id=str(uuid4()), project_id=project_id, chapter_id=chapter.id, document_id=document_id, segment_index=index, snapshot=snapshot))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = (await db.execute(query)).scalar_one_or_none()
        if not existing:
            raise
        return {"chapter_id": existing.chapter_id, "reused": True, "model_calls": 0}
    return {"chapter_id": chapter.id, "reused": False, "model_calls": 0}


@router.get("/chapters/{chapter_id}/source")
async def source(chapter_id: str, db=Depends(get_db)):
    if not await db.get(Chapter, chapter_id):
        raise HTTPException(404, "章节不存在")
    return await chapter_source(db, chapter_id)
