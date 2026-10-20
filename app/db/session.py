from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from app.core.config import settings

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

def get_db_engine() -> AsyncEngine:
    """Create or return the singleton async SQLAlchemy engine connected to Neon PostgreSQL."""
    global _engine
    if _engine is None:
        connection_url = settings.get_database_url()
        _engine = create_async_engine(
            connection_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )
    return _engine

def get_async_session_factory(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """Return an async sessionmaker instance using the shared connection pool."""
    global _session_factory
    if engine is not None:
        return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_db_engine(), expire_on_commit=False, class_=AsyncSession)
    return _session_factory

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session from the connection pool."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        yield session

async def close_db_engine():
    """Cleanly disposes the connection pool on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
