from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import ChapterRepository, PanelRepository, ProjectRepository
from app.models.schemas import (
    ChapterResponse,
    CreateChapterRequest,
    CreateProjectRequest,
    PanelResponse,
    ProjectResponse,
)


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.session = db
        self.project_repo = ProjectRepository(db)
        self.chapter_repo = ChapterRepository(db)

    async def create_project(self, user_id: str, data: CreateProjectRequest) -> ProjectResponse:
        project = await self.project_repo.create(user_id, data)
        return ProjectResponse.model_validate(project)

    async def get_project(self, project_id: str) -> ProjectResponse | None:
        project = await self.project_repo.get(project_id)
        if project:
            return ProjectResponse.model_validate(project)
        return None

    async def list_projects(self, user_id: str, limit: int = 10, offset: int = 0) -> list[ProjectResponse]:
        projects = await self.project_repo.list(user_id, limit, offset)
        return [ProjectResponse.model_validate(p) for p in projects]

    async def update_project(self, project_id: str, updates: dict) -> ProjectResponse | None:
        project = await self.project_repo.update(project_id, updates)
        if project:
            return ProjectResponse.model_validate(project)
        return None

    async def delete_project(self, project_id: str) -> bool:
        return await self.project_repo.delete(project_id)

    async def create_chapter(self, data: CreateChapterRequest) -> ChapterResponse:
        chapter = await self.chapter_repo.create(data)
        chapter_dict = {
            "id": chapter.id,
            "project_id": chapter.project_id,
            "title": chapter.title,
            "outline": chapter.outline,
            "storyboard": chapter.storyboard,
            "dialogues": chapter.dialogues,
            "phase": chapter.phase,
            "panels": [],
            "created_at": chapter.created_at,
            "updated_at": chapter.updated_at,
        }
        return ChapterResponse(**chapter_dict)

    async def get_chapter(self, chapter_id: str) -> ChapterResponse | None:
        chapter = await self.chapter_repo.get(chapter_id)
        if chapter:
            panel_repo = PanelRepository(self.session)
            panels = await panel_repo.list(chapter_id)
            chapter_dict = {
                "id": chapter.id,
                "project_id": chapter.project_id,
                "title": chapter.title,
                "outline": chapter.outline,
                "storyboard": chapter.storyboard,
                "dialogues": chapter.dialogues,
                "phase": chapter.phase,
                "panels": [PanelResponse.model_validate(p) for p in panels],
                "created_at": chapter.created_at,
                "updated_at": chapter.updated_at,
            }
            return ChapterResponse(**chapter_dict)
        return None

    async def list_chapters(self, project_id: str) -> list[ChapterResponse]:
        chapters = await self.chapter_repo.list(project_id)
        panel_repo = PanelRepository(self.session)
        results = []
        for chapter in chapters:
            panels = await panel_repo.list(chapter.id)
            chapter_dict = {
                "id": chapter.id,
                "project_id": chapter.project_id,
                "title": chapter.title,
                "outline": chapter.outline,
                "storyboard": chapter.storyboard,
                "dialogues": chapter.dialogues,
                "phase": chapter.phase,
                "panels": [PanelResponse.model_validate(p) for p in panels],
                "created_at": chapter.created_at,
                "updated_at": chapter.updated_at,
            }
            results.append(ChapterResponse(**chapter_dict))
        return results

    async def update_chapter(self, chapter_id: str, updates: dict) -> ChapterResponse | None:
        chapter = await self.chapter_repo.update(chapter_id, updates)
        if chapter:
            panel_repo = PanelRepository(self.session)
            panels = await panel_repo.list(chapter_id)
            chapter_dict = {
                "id": chapter.id,
                "project_id": chapter.project_id,
                "title": chapter.title,
                "outline": chapter.outline,
                "storyboard": chapter.storyboard,
                "dialogues": chapter.dialogues,
                "phase": chapter.phase,
                "panels": [PanelResponse.model_validate(p) for p in panels],
                "created_at": chapter.created_at,
                "updated_at": chapter.updated_at,
            }
            return ChapterResponse(**chapter_dict)
        return None
