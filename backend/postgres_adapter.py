"""
docs/01 — PostgreSQL + Qdrant migration scaffold.

This module is INTENTIONALLY a stub. It loads only when USE_POSTGRES=true.
Activates the migration path once Postgres + Qdrant are reachable.

The full migration playbook is in /app/docs/01_postgres_qdrant_migration.md.
Author: continue from here when production infra is provisioned.
"""
import os
import logging

logger = logging.getLogger("talktoplus.postgres")

USE_POSTGRES = os.environ.get("USE_POSTGRES", "false").lower() == "true"
POSTGRES_URL = os.environ.get("POSTGRES_URL", "")
QDRANT_URL = os.environ.get("QDRANT_URL", "")


async def init_postgres():
    """Initialize SQLAlchemy + run Alembic migrations.
    TODO: implement when Postgres infra ready. See docs/01."""
    if not USE_POSTGRES:
        return None
    if not POSTGRES_URL:
        logger.warning("USE_POSTGRES=true but POSTGRES_URL not set — staying on Mongo")
        return None
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(POSTGRES_URL, pool_size=10, max_overflow=20)
        # TODO: run migrations via Alembic
        logger.info("Postgres engine created (Alembic migrations: pending implementation)")
        return engine
    except ImportError:
        logger.error("sqlalchemy[asyncio] not installed — pip install sqlalchemy[asyncio] asyncpg alembic")
        return None


async def init_qdrant():
    """Initialize Qdrant async client and ensure collection exists.
    TODO: implement when Qdrant infra ready. See docs/01."""
    if not USE_POSTGRES or not QDRANT_URL:
        return None
    try:
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import VectorParams, Distance
        client = AsyncQdrantClient(url=QDRANT_URL)
        try:
            await client.get_collection("swarm_fragments")
        except Exception:
            await client.recreate_collection(
                "swarm_fragments",
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
        logger.info("Qdrant client ready")
        return client
    except ImportError:
        logger.error("qdrant-client not installed — pip install qdrant-client sentence-transformers")
        return None


# Tenant context manager for RLS
class TenantContext:
    """Sets PostgreSQL session var for Row-Level Security policy.
    Usage:
        async with TenantContext(session, tenant_id):
            result = await session.execute(select(Signal))
    """
    def __init__(self, session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def __aenter__(self):
        from sqlalchemy import text
        await self.session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": self.tenant_id})
        return self.session

    async def __aexit__(self, *args):
        pass
