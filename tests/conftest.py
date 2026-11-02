"""Isolate persistence before any app module can initialize its settings."""
import os
import tempfile
from pathlib import Path

temporary = Path(tempfile.mkdtemp(prefix="comic-studio-test-"))
os.environ["POSTGRES_URL"] = f"sqlite+aiosqlite:///{temporary / 'test.db'}"
os.environ["AI_PROVIDER"] = "chatgpt_desktop"
os.environ["IMAGE_PROVIDER"] = "chatgpt_desktop"
os.environ["IMAGE_EDIT_PROVIDER"] = "chatgpt_desktop"
for key in ("LOCAL_GPT_API_KEY", "IMAGE_API_KEY", "IMAGE_EDIT_API_KEY"):
    os.environ.pop(key, None)
os.environ["DEBUG"] = "false"
from app.core import paths

paths.MEDIA = temporary / "media"
paths.JOBS = temporary / "jobs"
paths.MEDIA.mkdir()
paths.JOBS.mkdir()


# Standalone adapter tests also need the request-accounting tables.
import pytest
import asyncio

@pytest.fixture(scope="session", autouse=True)
def initialized_schema():
    from app.db.session import init_db
    asyncio.run(init_db())


@pytest.fixture(autouse=True)
def forbid_unmocked_native_model_calls(monkeypatch):
    """A developer's saved automatic mode must never spend quota in pytest."""
    from app.tools.codex_rpc import client
    from app.core.config import settings
    import httpx
    for key in ("LOCAL_GPT_API_KEY", "IMAGE_API_KEY", "IMAGE_EDIT_API_KEY"):
        monkeypatch.setattr(settings, key, None)
    def denied(*args, **kwargs):
        raise AssertionError("Unit tests must mock native model execution")
    monkeypatch.setattr(client, "invoke", denied)
    original_send = httpx.AsyncClient.send
    async def guarded_send(self, *args, **kwargs):
        if not isinstance(self._transport, (httpx.MockTransport, httpx.ASGITransport)):
            raise AssertionError("Unit tests must mock provider HTTP transport")
        return await original_send(self, *args, **kwargs)
    monkeypatch.setattr(httpx.AsyncClient, "send", guarded_send)
