"""
TALK TO+ BDaaS — PostgreSQL + Qdrant adapter (production storage).

Activation:
  USE_POSTGRES=true in .env
  POSTGRES_URL=postgresql+asyncpg://...
  QDRANT_URL=http://localhost:6333

When activated, this module replaces motor calls in production routers.
The MongoDB path remains the canonical preview/dev path and is unchanged.

Migration plan: see /app/docs/01_postgres_qdrant_migration.md.
"""
import os
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger("talktoplus.postgres")

USE_POSTGRES = os.environ.get("USE_POSTGRES", "false").lower() == "true"
POSTGRES_URL = os.environ.get("POSTGRES_URL", "")
QDRANT_URL = os.environ.get("QDRANT_URL", "")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "swarm_fragments")
QDRANT_VECTOR_SIZE = int(os.environ.get("QDRANT_VECTOR_SIZE", "1024"))  # BGE-M3 = 1024

_engine = None
_qdrant = None
_session_factory = None


async def init_postgres():
    """Initialize SQLAlchemy async engine + session factory."""
    global _engine, _session_factory
    if not USE_POSTGRES or not POSTGRES_URL:
        return None
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    except ImportError:
        logger.error("sqlalchemy[asyncio] not installed — pip install 'sqlalchemy[asyncio]' asyncpg alembic")
        return None
    _engine = create_async_engine(POSTGRES_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("Postgres engine initialized")
    return _engine


async def init_qdrant():
    """Initialize Qdrant client and ensure swarm collection exists."""
    global _qdrant
    if not USE_POSTGRES or not QDRANT_URL:
        return None
    try:
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import VectorParams, Distance
    except ImportError:
        logger.error("qdrant-client not installed — pip install qdrant-client")
        return None
    _qdrant = AsyncQdrantClient(url=QDRANT_URL)
    try:
        await _qdrant.get_collection(QDRANT_COLLECTION)
    except Exception:
        await _qdrant.recreate_collection(
            QDRANT_COLLECTION,
            vectors_config=VectorParams(size=QDRANT_VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Qdrant collection '{QDRANT_COLLECTION}' created (dim={QDRANT_VECTOR_SIZE})")
    return _qdrant


def get_qdrant():
    return _qdrant


@asynccontextmanager
async def session_for_tenant(tenant_id: str):
    """Yield a SQLAlchemy session with PostgreSQL RLS context applied.

    Usage:
        async with session_for_tenant(user["tenant_id"]) as session:
            result = await session.execute(select(Signal))
    """
    if _session_factory is None:
        raise RuntimeError("Postgres not initialized — set USE_POSTGRES=true and call init_postgres()")
    from sqlalchemy import text
    async with _session_factory() as session:
        await session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def shutdown_postgres():
    if _engine is not None:
        await _engine.dispose()
    if _qdrant is not None:
        await _qdrant.close()
