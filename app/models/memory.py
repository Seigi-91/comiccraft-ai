from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CharacterMemory(BaseModel):
    id: str
    name: str
    description: str
    appearance: Dict[str, Any]
    personality: str
    relationships: Dict[str, str]
    voice: str
    ip_adapter_embedding: Optional[str] = None
    created_at: datetime = datetime.utcnow()


class StoryEvent(BaseModel):
    id: str
    chapter_id: str
    summary: str
    key_points: List[str]
    character_changes: Dict[str, Any] = {}
    timestamp: datetime = datetime.utcnow()


class StyleReference(BaseModel):
    id: str
    name: str
    url: str
    description: str
    features: List[str] = []


class MemoryStore:
    def __init__(self):
        self.characters: Dict[str, CharacterMemory] = {}
        self.events: List[StoryEvent] = []
        self.style_references: Dict[str, StyleReference] = {}

    async def add_character(self, character: CharacterMemory):
        self.characters[character.id] = character

    async def get_character(self, character_id: str) -> Optional[CharacterMemory]:
        return self.characters.get(character_id)

    async def update_character(self, character_id: str, updates: Dict[str, Any]):
        if character_id in self.characters:
            character = self.characters[character_id]
            for key, value in updates.items():
                setattr(character, key, value)

    async def add_event(self, event: StoryEvent):
        self.events.append(event)

    async def get_recent_events(self, chapter_id: Optional[str] = None, limit: int = 10) -> List[StoryEvent]:
        events = self.events
        if chapter_id:
            events = [e for e in events if e.chapter_id == chapter_id]
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    async def add_style_reference(self, style: StyleReference):
        self.style_references[style.id] = style

    async def get_style_reference(self, style_id: str) -> Optional[StyleReference]:
        return self.style_references.get(style_id)

    async def get_all_characters(self) -> List[CharacterMemory]:
        return list(self.characters.values())

    async def get_all_styles(self) -> List[StyleReference]:
        return list(self.style_references.values())
