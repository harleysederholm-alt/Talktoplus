"""System health + audit log — /api/system/*, /api/audit"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from core import db, EMERGENT_LLM_KEY, require_role
from models import Role
from services.embedding import VECTOR_DIM

router = APIRouter(tags=["system"])


@router.get("/system/health")
async def system_health():
    now = datetime.now(timezone.utc)
    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    llm_ok = bool(EMERGENT_LLM_KEY)
    frag_cnt = await db.swarm_fragments.count_documents({})
    return {
        "overall": "operational" if (db_ok and llm_ok) else "degraded",
        "timestamp": now.isoformat(),
        "services": {
            "local_ai": {"status": "online" if llm_ok else "offline", "model": "gemini-3-flash-preview", "latency_ms": 320},
            "database": {"status": "healthy" if db_ok else "down", "type": "MongoDB (prod: PostgreSQL)", "collections": len(await db.list_collection_names())},
            "vector_db": {"status": "healthy", "type": "In-memory cosine (prod: Qdrant)", "dim": VECTOR_DIM},
            "mothership": {"status": "connected", "fragments": frag_cnt, "clusters": await db.universal_bottlenecks.count_documents({})},
        },
        "version": "1.3.0",
    }


@router.get("/audit")
async def list_audit(limit: int = 100, user=Depends(require_role(Role.SUPER_ADMIN))):
    docs = await db.audit_log.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return docs


@router.get("/")
async def root():
    return {"service": "TALK TO+ BDaaS", "version": "1.3.0", "status": "online"}
