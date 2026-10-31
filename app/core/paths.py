from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
MEDIA = DATA / "media"
JOBS = DATA / "chatgpt_jobs"
for directory in (MEDIA, JOBS):
    directory.mkdir(parents=True, exist_ok=True)
