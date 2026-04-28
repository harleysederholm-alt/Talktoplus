"""Signals router — /api/signals/*"""
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user, audit
from models import Signal, SignalCreate, ValidationReq, SignalStatus, RiskLevel
from services.signal_pipeline import analyze_and_store_signal
from services.embedding import sector_hash
from services.swarm import update_clusters, query_universal_patterns
from services.ai import generate_action_card_ai

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("", response_model=Signal)
async def create_signal(body: SignalCreate, user=Depends(get_current_user)):
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": sid, "tenant_id": user["tenant_id"],
        "content": body.content, "source": body.source,
        "business_unit": body.business_unit,
        "author": body.author or user["full_name"],
        "submitted_at": now,
        "status": SignalStatus.PENDING.value,
        "risk_level": None, "confidence": None, "summary": None,
        "execution_gaps": [], "hidden_assumptions": [], "facilitator_questions": [],
        "category": None, "semantic_vector": None,
        "validated_by": None, "validated_at": None, "validation_note": None,
        "override_risk_level": None, "swarm_fragment_id": None, "action_card_id": None,
    }
    await db.signals.insert_one(doc.copy())
    await analyze_and_store_signal(sid, user["tenant_id"], body.content)
    s = await db.signals.find_one({"id": sid}, {"_id": 0})
    return Signal(**s)


@router.get("", response_model=List[Signal])
async def list_signals(
    status_: Optional[SignalStatus] = None,
    limit: int = 100,
    user=Depends(get_current_user),
):
    q = {"tenant_id": user["tenant_id"]}
    if status_:
        q["status"] = status_.value
    docs = await db.signals.find(q, {"_id": 0}).sort("submitted_at", -1).limit(limit).to_list(limit)
    return [Signal(**d) for d in docs]


@router.get("/{sid}", response_model=Signal)
async def get_signal(sid: str, user=Depends(get_current_user)):
    s = await db.signals.find_one({"id": sid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Signal not found")
    return Signal(**s)


@router.post("/{sid}/validate", response_model=Signal)
async def validate_signal(sid: str, body: ValidationReq, user=Depends(get_current_user)):
    s = await db.signals.find_one({"id": sid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Signal not found")
    if s["status"] != SignalStatus.PENDING.value:
        raise HTTPException(400, "Signal already processed")
    now = datetime.now(timezone.utc)
    if body.decision == "dismiss":
        await db.signals.update_one({"id": sid}, {"$set": {
            "status": SignalStatus.DISMISSED.value,
            "validated_by": user["full_name"], "validated_at": now,
            "validation_note": body.note,
        }})
        out = await db.signals.find_one({"id": sid}, {"_id": 0})
        return Signal(**out)

    if body.decision in ("escalate", "in_progress"):
        new_status = SignalStatus.ESCALATED if body.decision == "escalate" else SignalStatus.IN_PROGRESS
        await db.signals.update_one({"id": sid}, {"$set": {
            "status": new_status.value,
            "validated_by": user["full_name"], "validated_at": now,
            "validation_note": body.note,
        }})
        out = await db.signals.find_one({"id": sid}, {"_id": 0})
        return Signal(**out)

    new_status = SignalStatus.OVERRIDDEN if body.decision == "override" else SignalStatus.VALIDATED
    final_risk = body.override_risk_level.value if (body.decision == "override" and body.override_risk_level) else s["risk_level"]

    tenant = await db.tenants.find_one({"id": s["tenant_id"]}, {"_id": 0})
    sh = tenant["sector_hash"] if tenant else sector_hash("unknown")
    frag_id = str(uuid.uuid4())
    await db.swarm_fragments.insert_one({
        "id": frag_id,
        "sector_hash": sh,
        "sector_display": tenant["sector"] if tenant else "Unknown",
        "risk_level": final_risk,
        "confidence": s.get("confidence") or 0.6,
        "category": s.get("category") or "process",
        "semantic_vector": s.get("semantic_vector") or [],
        "created_at": now,
    })

    patterns = await query_universal_patterns(s.get("semantic_vector") or [], s["tenant_id"])

    card_data = await generate_action_card_ai(s.get("summary") or s["content"][:300], s.get("execution_gaps") or [], patterns)
    card_id = str(uuid.uuid4())
    await db.action_cards.insert_one({
        "id": card_id,
        "tenant_id": s["tenant_id"],
        "signal_id": sid,
        "title": card_data["title"],
        "summary": card_data["summary"],
        "playbook": card_data["playbook"],
        "rag_context_used": [],
        "swarm_patterns_used": patterns,
        "impact_score": None,
        "swarm_verified": len(patterns) > 0,
        "created_at": now,
    })

    await db.signals.update_one({"id": sid}, {"$set": {
        "status": new_status.value,
        "validated_by": user["full_name"], "validated_at": now,
        "validation_note": body.note,
        "override_risk_level": body.override_risk_level.value if body.override_risk_level else None,
        "swarm_fragment_id": frag_id,
        "action_card_id": card_id,
    }})

    await audit("signal.validated", user["id"], s["tenant_id"], {
        "signal_id": sid, "decision": body.decision, "final_risk": final_risk, "card_id": card_id,
    })

    asyncio.create_task(update_clusters())

    out = await db.signals.find_one({"id": sid}, {"_id": 0})
    return Signal(**out)
