"""Per-task callbacks avoid putting runtime callables into persisted graph state."""
from contextvars import ContextVar
panel_progress=ContextVar("panel_progress",default=None)
