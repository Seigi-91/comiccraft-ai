from .characters import router as characters_router
from .projects import router as projects_router
from .tasks import router as tasks_router
from .websocket import router as websocket_router

projects = projects_router
tasks = tasks_router
websocket = websocket_router
characters = characters_router
