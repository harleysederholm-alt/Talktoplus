"""Swarm router — /api/swarm/*"""
from typing import List
from fastapi import APIRouter, Depends

from core import db, get_current_user, require_role
from models import UniversalBottleneck, Role
from services.swarm import update_clusters

router = APIRouter(prefix="/swarm", tags=["swarm"])


@router.get("/bottlenecks", response_model=List[UniversalBottleneck])
async def bottlenecks(user=Depends(get_current_user)):
    docs = await db.universal_bottlenecks.find({}, {"_id": 0}).sort("fragment_count", -1).to_list(50)
    seen = {}
    for d in docs:
        if d["category"] not in seen or d["fragment_count"] > seen[d["category"]]["fragment_count"]:
            seen[d["category"]] = d
    return [UniversalBottleneck(**d) for d in seen.values()]


@router.get("/fragments/count")
async def fragment_count(user=Depends(get_current_user)):
    return {"count": await db.swarm_fragments.count_documents({})}


@router.post("/recompute")
async def recompute(user=Depends(require_role(Role.SUPER_ADMIN))):
    await update_clusters()
    return {"ok": True}
