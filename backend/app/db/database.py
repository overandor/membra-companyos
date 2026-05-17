"""MEMBRA CompanyOS — Database configuration."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# Import the unified Base from models so all tables are registered
from app.models.base import Base

# Import all models to ensure they're registered with metadata
import app.models.agent
import app.models.company
import app.models.governance
import app.models.intent
import app.models.job
import app.models.proofbook
import app.models.task
import app.models.worldbridge
import app.models.opportunity

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency yielding an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables at startup (dev/staging only)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
