"""Webhook router — /api/webhook/{tenant_id}"""
import uuid
import json
import hmac
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Request

from core import db, limiter, WEBHOOK_SECRET, WEBHOOK_STRICT
from models import SignalStatus
from services.signal_pipeline import analyze_and_store_signal

router = APIRouter(prefix="/webhook", tags=["webhook"])


def verify_hmac(raw: bytes, sig_header: Optional[str]) -> bool:
    if not sig_header:
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header.replace("sha256=", ""))


@router.post("/{tenant_id}")
@limiter.limit("60/minute")
async def webhook_receive(
    request: Request,
    tenant_id: str,
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
    x_nonce: Optional[str] = Header(None),
    x_source: Optional[str] = Header("howspace"),
):
    raw = await request.body()
    if WEBHOOK_STRICT:
        if not x_signature or not verify_hmac(raw, x_signature):
            raise HTTPException(401, "Invalid HMAC")
        try:
            ts = int(x_timestamp or "0")
            now_s = int(datetime.now(timezone.utc).timestamp())
            if abs(now_s - ts) > 300:
                raise HTTPException(401, "Stale timestamp")
        except ValueError:
            raise HTTPException(401, "Invalid timestamp")
        if not x_nonce:
            raise HTTPException(401, "Missing nonce")
        if await db.webhook_nonces.find_one({"nonce": x_nonce}):
            raise HTTPException(409, "Replay detected")
        await db.webhook_nonces.insert_one({
            "nonce": x_nonce, "tenant_id": tenant_id,
            "created_at": datetime.now(timezone.utc),
        })
    else:
        if x_signature and not verify_hmac(raw, x_signature):
            raise HTTPException(401, "Invalid HMAC")
    try:
        payload = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    if x_source == "howspace":
        msg = payload.get("event", {}).get("message", payload) if isinstance(payload.get("event"), dict) else payload
        content = msg.get("text") or payload.get("content") or payload.get("message") or ""
        author = (msg.get("author", {}) or {}).get("name") if isinstance(msg.get("author"), dict) else msg.get("author") or payload.get("author", "Howspace User")
        bu = (payload.get("workspace") or {}).get("name") if isinstance(payload.get("workspace"), dict) else payload.get("business_unit", "Unknown")
    elif x_source == "teams":
        content = payload.get("text") or payload.get("content") or ""
        author = (payload.get("from") or {}).get("name", "Teams User")
        bu = payload.get("channel", payload.get("business_unit", "Teams"))
    else:
        content = payload.get("content") or payload.get("message") or ""
        author = payload.get("author", "Webhook")
        bu = payload.get("business_unit", "Unknown")
    if not content:
        raise HTTPException(400, "Missing content")
    if not await db.tenants.find_one({"id": tenant_id}):
        raise HTTPException(404, "Unknown tenant")
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": sid, "tenant_id": tenant_id,
        "content": content, "source": x_source or "webhook",
        "business_unit": bu, "author": author,
        "submitted_at": now,
        "status": SignalStatus.PENDING.value,
        "risk_level": None, "confidence": None, "summary": None,
        "execution_gaps": [], "hidden_assumptions": [], "facilitator_questions": [],
        "category": None, "semantic_vector": None,
        "validated_by": None, "validated_at": None, "validation_note": None,
        "override_risk_level": None, "swarm_fragment_id": None, "action_card_id": None,
    }
    await db.signals.insert_one(doc.copy())
    asyncio.create_task(analyze_and_store_signal(sid, tenant_id, content))
    return {"accepted": True, "signal_id": sid}
