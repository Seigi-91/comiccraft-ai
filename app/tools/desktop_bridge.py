"""Durable handoff. Never use private ChatGPT endpoints or desktop tokens."""

import hashlib
import json
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from app.core.paths import JOBS

task_context = ContextVar("comic_task", default="standalone")
stage_context = ContextVar("comic_stage", default="assistant")


class PendingChatGPT(Exception):
    def __init__(self, job):
        self.job = job
        super().__init__("等待 ChatGPT 返回结果")


def read_job(job_id):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise FileNotFoundError("Invalid job id")
    return json.loads((JOBS / f"{job_id}.json").read_text(encoding="utf-8"))


def save_job(job):
    path = JOBS / f"{job['id']}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def request_chatgpt(kind, prompt, images=None):
    task_id, stage = task_context.get(), stage_context.get()
    identity = json.dumps([task_id, stage, kind, prompt, images or []], ensure_ascii=False)
    job_id = hashlib.sha256(identity.encode()).hexdigest()[:32]
    try:
        job = read_job(job_id)
    except FileNotFoundError:
        job = {
            "id": job_id,
            "task_id": task_id,
            "stage": stage,
            "kind": kind,
            "prompt": prompt,
            "images": images or [],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        save_job(job)
    if job["status"] == "completed":
        return job["response"]
    raise PendingChatGPT(job)


def list_jobs(task_id=None):
    jobs = [json.loads(p.read_text(encoding="utf-8")) for p in JOBS.glob("*.json")]
    return sorted(
        [j for j in jobs if not task_id or j["task_id"] == task_id], key=lambda j: j["created_at"]
    )
