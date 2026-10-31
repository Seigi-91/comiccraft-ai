from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.paths import ROOT
from app.models.orm import Base

if settings.POSTGRES_URL:
    database_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    database_url = f"sqlite+aiosqlite:///{ROOT / 'comic_agent.db'}"

engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
