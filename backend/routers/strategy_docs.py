"""Strategy RAG docs — /api/strategy-docs/*"""
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user
from models import StrategyDoc, StrategyDocCreate
from services.embedding import semantic_embed

router = APIRouter(prefix="/strategy-docs", tags=["strategy-docs"])


@router.get("", response_model=List[StrategyDoc])
async def list_docs(user=Depends(get_current_user)):
    docs = await db.strategy_docs.find({"tenant_id": user["tenant_id"]}, {"_id": 0, "vector": 0})\
        .sort("created_at", -1).to_list(200)
    return [StrategyDoc(**d) for d in docs]


@router.post("", response_model=StrategyDoc)
async def create_doc(body: StrategyDocCreate, user=Depends(get_current_user)):
    did = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    vec = semantic_embed(body.content[:4000])
    doc = {
        "id": did, "tenant_id": user["tenant_id"],
        "title": body.title, "content": body.content,
        "chunks": max(1, len(body.content) // 500),
        "uploaded_by": user["full_name"], "created_at": now,
        "vector": vec,
    }
    await db.strategy_docs.insert_one(doc.copy())
    doc.pop("vector")
    return StrategyDoc(**doc)


@router.delete("/{did}")
async def delete_doc(did: str, user=Depends(get_current_user)):
    r = await db.strategy_docs.delete_one({"id": did, "tenant_id": user["tenant_id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}
