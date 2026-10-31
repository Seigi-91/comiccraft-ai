from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.api.routes import characters, projects, tasks, websocket
from app.api.routes.studio import router as studio
from app.api.routes.editing import router as editing
from app.api.routes.repairs import router as repairs
from app.api.routes.production import router as production
from app.core.config import settings
from app.core.paths import ROOT, MEDIA
from app.db.session import init_db, AsyncSessionLocal
from app.models.orm import Task, TaskStatus


@asynccontextmanager
async def lifespan(app):
    await init_db()
    async with AsyncSessionLocal() as session:
        unfinished = (
            await session.execute(
                select(Task).where(Task.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]))
            )
        ).scalars()
        for task in unfinished:
            task.status = TaskStatus.FAILED
            task.error_message = "服务已重启；点击继续任务可从保存的阶段恢复。"
        from app.models.orm import PanelRepair
        interrupted=(await session.execute(select(PanelRepair).where(PanelRepair.status=="pending"))).scalars()
        for repair in interrupted:
            repair.status="failed"
            repair.error="服务已重启，原图未改变，请重新创建精修任务。"
        from app.models.orm import ProductionBatch,ProductionRecord
        records=(await session.execute(select(ProductionRecord).where(ProductionRecord.status=="requested"))).scalars()
        for record in records:
            record.status="failed"
            record.error="服务重启中断了请求，请检查任务后重试"
        batches=(await session.execute(select(ProductionBatch).where(ProductionBatch.status=="running"))).scalars()
        for batch in batches:
            batch.status="paused"
        await session.commit()
    yield


app = FastAPI(title="ComicCraft AI", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects, prefix="/api/projects")
app.include_router(characters, prefix="/api/projects")
app.include_router(tasks, prefix="/api/tasks")
app.include_router(websocket, prefix="/api/ws")
app.include_router(studio, prefix="/api/studio")
app.include_router(editing, prefix="/api/editing")
app.include_router(repairs, prefix="/api/repairs")
app.include_router(production, prefix="/api/production")
app.mount("/media", StaticFiles(directory=str(MEDIA)), name="media")
app.mount("/static", StaticFiles(directory=str(ROOT / "app/static")), name="static")


@app.get("/health")
async def health():
    return {"status": "healthy", "provider": settings.AI_PROVIDER}


dist = ROOT / "frontend/dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")


@app.get("/{path:path}")
async def website(path: str):
    if path.startswith(("api/", "media/", "assets/")):
        raise HTTPException(404, "Not found")
    if not (dist / "index.html").exists():
        return {"message": "请先运行 frontend 中的 npm run build，或使用 http://localhost:5173"}
    return FileResponse(dist / "index.html")


def main():
    import uvicorn

    uvicorn.run(
        "app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
