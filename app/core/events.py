from enum import Enum
from typing import Any


class EventType(str, Enum):
    PROJECT_CREATED = "project_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    PANEL_GENERATED = "panel_generated"
    PANEL_REVIEWED = "panel_reviewed"
    HUMAN_INTERVENTION_NEEDED = "human_intervention_needed"
    HUMAN_FIX_SUBMITTED = "human_fix_submitted"


class Event:
    def __init__(self, event_type: EventType, data: dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class EventBus:
    def __init__(self):
        self._subscribers: dict[EventType, list] = {}

    def subscribe(self, event_type: EventType, handler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event):
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                pass


event_bus = EventBus()
