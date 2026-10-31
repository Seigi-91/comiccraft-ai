from celery import Celery
from app.core.config import settings
import asyncio

app = Celery(
    "comic_agent_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.timezone = "UTC"
app.conf.enable_utc = True


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task
def generate_panel_task(storyboard_data: dict, style_refs: list, character_refs: list) -> dict:
    from app.agents.panel_designer import PanelDesignerAgent

    designer = PanelDesignerAgent()
    panels = run_async(designer.generate_panels(storyboard_data, style_refs, character_refs))
    return panels


@app.task
def review_panel_task(panel_data: dict, style_refs: list) -> dict:
    from app.agents.style_reviewer import StyleReviewerAgent

    reviewer = StyleReviewerAgent()
    result = run_async(reviewer.review_panels([panel_data], style_refs))
    return result


@app.task
def inpaint_panel_task(image_url: str, mask_url: str, prompt: str) -> str:
    from app.tools.sd_client import SDClient

    sd_client = SDClient()
    result = sd_client.inpaint(image_url, mask_url, prompt)
    return result
