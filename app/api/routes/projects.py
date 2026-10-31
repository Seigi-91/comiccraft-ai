from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import (
    ChapterResponse,
    CreateChapterRequest,
    CreateProjectRequest,
    ProjectResponse,
)
from app.services.project_service import ProjectService

router = APIRouter()


@router.post("", response_model=ProjectResponse)
async def create_project(
    data: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    return await service.create_project(user_id="default_user", data=data)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user_id: str = "default_user",
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    return await service.list_projects(user_id, limit, offset)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    updates: dict,
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.update_project(project_id, updates)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    success = await service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/chapters", response_model=ChapterResponse)
async def create_chapter(
    project_id: str,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    if not await service.get_project(project_id):
        raise HTTPException(404, "项目不存在")
    title = payload.get("title", "").strip()
    if not title or len(title) > 200:
        raise HTTPException(422, "请输入 1–200 字的章节标题")
    data = CreateChapterRequest(project_id=project_id, title=title)
    return await service.create_chapter(data)


@router.get("/{project_id}/chapters", response_model=list[ChapterResponse])
async def list_chapters(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    return await service.list_chapters(project_id)


@router.get("/{project_id}/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    project_id: str,
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    chapter = await service.get_chapter(chapter_id)
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
