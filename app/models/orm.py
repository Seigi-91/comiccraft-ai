from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_HUMAN = "needs_human"


class PanelStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    REVIEWING = "reviewing"
    PASSED = "passed"
    FAILED = "failed"
    FIXING = "fixing"


class Phase(str, Enum):
    PLANNING = "planning"
    STORYBOARDING = "storyboarding"
    DIALOGUE = "dialogue"
    PANEL_GENERATION = "panel_generation"
    REVIEW = "review"
    LAYOUT = "layout"
    COMPLETED = "completed"


Base: Any = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    inspiration: Mapped[Optional[str]] = mapped_column(Text)
    style_ref_urls: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[ProjectStatus] = mapped_column(SQLAlchemyEnum(ProjectStatus), default=ProjectStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    chapters = relationship("Chapter", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    character_profiles = relationship("CharacterProfile", back_populates="project")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    outline: Mapped[Optional[dict]] = mapped_column(JSON)
    storyboard: Mapped[Optional[dict]] = mapped_column(JSON)
    dialogues: Mapped[Optional[dict]] = mapped_column(JSON)
    phase: Mapped[Phase] = mapped_column(SQLAlchemyEnum(Phase), default=Phase.PLANNING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    project = relationship("Project", back_populates="chapters")
    panels = relationship("Panel", back_populates="chapter")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    chapter_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("chapters.id"))
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SQLAlchemyEnum(TaskStatus), default=TaskStatus.PENDING)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    project = relationship("Project", back_populates="tasks")
    chapter = relationship("Chapter")


class Panel(Base):
    __tablename__ = "panels"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    chapter_id: Mapped[str] = mapped_column(String, ForeignKey("chapters.id"))
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[PanelStatus] = mapped_column(SQLAlchemyEnum(PanelStatus), default=PanelStatus.PENDING)
    review_result: Mapped[Optional[dict]] = mapped_column(JSON)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    chapter = relationship("Chapter", back_populates="panels")


class CharacterProfile(Base):
    __tablename__ = "character_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    appearance_description: Mapped[Optional[str]] = mapped_column(Text)
    reference_image_url: Mapped[Optional[str]] = mapped_column(String)
    face_mask_url: Mapped[Optional[str]] = mapped_column(String)
    face_bbox: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_adapter_embedding: Mapped[Optional[dict]] = mapped_column(JSON)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    project = relationship("Project", back_populates="character_profiles")


class ChapterVersion(Base):
    __tablename__ = "chapter_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    chapter_id: Mapped[str] = mapped_column(String, ForeignKey("chapters.id"), index=True)
    label: Mapped[str] = mapped_column(String)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class CharacterDetails(Base):
    __tablename__ = "character_details"
    character_id: Mapped[str] = mapped_column(String, ForeignKey("character_profiles.id"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class PanelRepair(Base):
    __tablename__ = "panel_repairs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    chapter_id: Mapped[str] = mapped_column(String, ForeignKey("chapters.id"), index=True)
    panel_index: Mapped[int] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(String)
    mask_url: Mapped[str] = mapped_column(String)
    job_id: Mapped[Optional[str]] = mapped_column(String)
    candidate_url: Mapped[Optional[str]] = mapped_column(String)
    instructions: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ProductionRecord(Base):
    __tablename__ = "production_records"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    chapter_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    task_id: Mapped[str] = mapped_column(String, index=True)
    panel_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    origin: Mapped[str] = mapped_column(String)
    settings_snapshot: Mapped[dict] = mapped_column(JSON)
    image_url: Mapped[Optional[str]] = mapped_column(String)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ProductionBatch(Base):
    __tablename__ = "production_batches"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="paused")
    items: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
