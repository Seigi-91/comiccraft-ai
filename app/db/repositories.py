from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import (
    Chapter,
    CharacterProfile,
    Panel,
    PanelStatus,
    Phase,
    Project,
    ProjectStatus,
    Task,
    TaskStatus,
)
from app.models.schemas import CreateChapterRequest, CreateProjectRequest


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: str, data: CreateProjectRequest) -> Project:
        project = Project(
            id=str(uuid4()),
            user_id=user_id,
            name=data.name,
            description=data.description,
            inspiration=data.inspiration,
            style_ref_urls=data.style_ref_urls,
            status=ProjectStatus.DRAFT,
        )
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get(self, project_id: str) -> Project | None:
        result = await self.session.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def list(self, user_id: str, limit: int = 10, offset: int = 0) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, project_id: str, updates: dict) -> Project | None:
        project = await self.get(project_id)
        if project:
            allowed = {"name", "description", "inspiration", "style_ref_urls", "status"}
            for key, value in updates.items():
                if key in allowed:
                    setattr(project, key, value)
            await self.session.commit()
            await self.session.refresh(project)
        return project

    async def delete(self, project_id: str) -> bool:
        project = await self.get(project_id)
        if project:
            await self.session.delete(project)
            await self.session.commit()
            return True
        return False


class ChapterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: CreateChapterRequest) -> Chapter:
        chapter = Chapter(
            id=str(uuid4()),
            project_id=data.project_id,
            title=data.title,
            phase=Phase.PLANNING,
        )
        self.session.add(chapter)
        await self.session.commit()
        await self.session.refresh(chapter)
        return chapter

    async def get(self, chapter_id: str) -> Chapter | None:
        result = await self.session.execute(select(Chapter).where(Chapter.id == chapter_id))
        return result.scalar_one_or_none()

    async def list(self, project_id: str) -> list[Chapter]:
        result = await self.session.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.created_at)
        )
        return list(result.scalars().all())

    async def update(self, chapter_id: str, updates: dict) -> Chapter | None:
        chapter = await self.get(chapter_id)
        if chapter:
            for key, value in updates.items():
                setattr(chapter, key, value)
            await self.session.commit()
            await self.session.refresh(chapter)
        return chapter


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: str, chapter_id: str | None, task_type: str) -> Task:
        task = Task(
            id=str(uuid4()),
            project_id=project_id,
            chapter_id=chapter_id,
            type=task_type,
            status=TaskStatus.PENDING,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get(self, task_id: str) -> Task | None:
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def update(self, task_id: str, updates: dict) -> Task | None:
        task = await self.get(task_id)
        if task:
            for key, value in updates.items():
                setattr(task, key, value)
            await self.session.commit()
            await self.session.refresh(task)
        return task

    async def set_status(self, task_id: str, status: TaskStatus) -> Task | None:
        return await self.update(task_id, {"status": status})


class PanelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, chapter_id: str, index: int) -> Panel:
        panel = Panel(
            id=str(uuid4()),
            chapter_id=chapter_id,
            index=index,
            status=PanelStatus.PENDING,
        )
        self.session.add(panel)
        await self.session.commit()
        await self.session.refresh(panel)
        return panel

    async def get(self, panel_id: str) -> Panel | None:
        result = await self.session.execute(select(Panel).where(Panel.id == panel_id))
        return result.scalar_one_or_none()

    async def list(self, chapter_id: str) -> list[Panel]:
        result = await self.session.execute(
            select(Panel)
            .where(Panel.chapter_id == chapter_id)
            .order_by(Panel.index)
        )
        return list(result.scalars().all())

    async def update(self, panel_id: str, updates: dict) -> Panel | None:
        panel = await self.get(panel_id)
        if panel:
            for key, value in updates.items():
                setattr(panel, key, value)
            await self.session.commit()
            await self.session.refresh(panel)
        return panel


class CharacterProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: str, name: str, appearance_description: str = "") -> CharacterProfile:
        profile = CharacterProfile(
            id=str(uuid4()),
            project_id=project_id,
            name=name,
            appearance_description=appearance_description,
            is_confirmed=False,
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def get(self, profile_id: str) -> CharacterProfile | None:
        result = await self.session.execute(select(CharacterProfile).where(CharacterProfile.id == profile_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, project_id: str, name: str) -> CharacterProfile | None:
        result = await self.session.execute(
            select(CharacterProfile).where(
                CharacterProfile.project_id == project_id,
                CharacterProfile.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list(self, project_id: str) -> list[CharacterProfile]:
        result = await self.session.execute(
            select(CharacterProfile).where(CharacterProfile.project_id == project_id)
        )
        return list(result.scalars().all())

    async def update(self, profile_id: str, updates: dict) -> CharacterProfile | None:
        profile = await self.get(profile_id)
        if profile:
            for key, value in updates.items():
                setattr(profile, key, value)
            await self.session.commit()
            await self.session.refresh(profile)
        return profile

    async def confirm(self, profile_id: str) -> CharacterProfile | None:
        return await self.update(profile_id, {"is_confirmed": True})

    async def delete(self, profile_id: str) -> bool:
        profile = await self.get(profile_id)
        if profile:
            await self.session.delete(profile)
            await self.session.commit()
            return True
        return False
