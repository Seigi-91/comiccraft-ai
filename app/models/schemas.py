from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    inspiration: Optional[str] = None
    style_ref_urls: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    inspiration: Optional[str] = None
    style_ref_urls: Optional[List[str]] = None
    status: str
    created_at: datetime
    updated_at: datetime


class CreateChapterRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)


class PanelResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    chapter_id: str
    index: int
    image_url: Optional[str] = None
    status: str
    review_result: Optional[Dict[str, Any]] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime


class ChapterResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    title: str
    outline: Optional[Dict[str, Any]] = None
    storyboard: Optional[Dict[str, Any]] = None
    dialogues: Optional[Dict[str, Any]] = None
    phase: str
    panels: List[PanelResponse] = []
    created_at: datetime
    updated_at: datetime


class GenerateChapterRequest(BaseModel):
    project_id: str
    chapter_id: str


class TaskResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    chapter_id: Optional[str] = None
    type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime


class HumanFixRequest(BaseModel):
    panel_id: str
    instructions: str
    fixed_image_url: Optional[str] = None


class StorySchema(BaseModel):
    title: str
    world_view: str
    outline: List[Dict[str, Any]]
    characters: List[Dict[str, Any]]


class StoryboardPanel(BaseModel):
    model_config = {"extra": "allow"}
    index: int
    shot_type: str
    perspective: str
    composition: Dict[str, Any]
    action: str
    dialogue_ref: Optional[str] = None


class StoryboardSchema(BaseModel):
    panels: List[StoryboardPanel]
    layout_type: str


class BubblePosition(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class BubbleSize(BaseModel):
    width: float = Field(ge=8, le=98)
    height: float = Field(ge=4, le=98)


class DialogueBubble(BaseModel):
    panel_index: int
    text: str
    character: Optional[str] = None
    bubble_type: str
    position: BubblePosition
    tail: Optional[BubblePosition] = None
    size: Optional[BubbleSize] = None
    font_size: int = Field(default=26, ge=12, le=60)


class DialogueSchema(BaseModel):
    bubbles: List[DialogueBubble]


class ReviewIssue(BaseModel):
    type: str
    severity: str
    description: str
    suggestion: Optional[str] = None


class ReviewResult(BaseModel):
    passed: bool
    issues: List[ReviewIssue]
    score: float = Field(ge=0, le=100)


class PanelSchema(BaseModel):
    id: str
    index: int
    image_url: Optional[str] = None
    status: str
    review_result: Optional[ReviewResult] = None
    retry_count: int


class ComicState(BaseModel):
    project_id: str
    user_id: str
    inspiration: Optional[str] = None
    style_ref_urls: Optional[List[str]] = None
    outline: Optional[StorySchema] = None
    chapters: List[ChapterResponse] = []
    storyboard: Optional[StoryboardSchema] = None
    dialogues: Optional[DialogueSchema] = None
    panels: List[PanelSchema] = []
    current_chapter: Optional[str] = None
    phase: str = "planning"
    review_history: List[ReviewResult] = []
    retry_count: int = 0
    human_intervene: bool = False
