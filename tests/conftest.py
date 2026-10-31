"""Isolate persistence before any app module can initialize its settings."""
import os
import tempfile
from pathlib import Path

temporary = Path(tempfile.mkdtemp(prefix="comic-studio-test-"))
os.environ["POSTGRES_URL"] = f"sqlite+aiosqlite:///{temporary / 'test.db'}"
os.environ["AI_PROVIDER"] = "chatgpt_desktop"
os.environ["DEBUG"] = "false"
from app.core import paths

paths.MEDIA = temporary / "media"
paths.JOBS = temporary / "jobs"
paths.MEDIA.mkdir()
paths.JOBS.mkdir()
