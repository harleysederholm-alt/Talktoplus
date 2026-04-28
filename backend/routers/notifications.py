"""Notifications router — /api/notifications/*"""
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user
from models import NotificationChannel, NotificationCreate
from services.notifications import (
    encrypt_url, decrypt_url, slack_blocks, teams_card, post_webhook,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationChannel])
async def list_notifications(user=Depends(get_current_user)):
    docs = await db.notification_channels.find(
        {"tenant_id": user["tenant_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    for d in docs:
        d["webhook_url"] = decrypt_url(d["webhook_url"])
    return [NotificationChannel(**d) for d in docs]


@router.post("", response_model=NotificationChannel)
async def create_notification(body: NotificationCreate, user=Depends(get_current_user)):
    nid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": nid, "tenant_id": user["tenant_id"],
        "type": body.type, "webhook_url": encrypt_url(body.webhook_url),
        "min_severity": body.min_severity.value, "enabled": True,
        "created_at": now, "label": body.label,
    }
    await db.notification_channels.insert_one(doc.copy())
    doc["webhook_url"] = body.webhook_url
    return NotificationChannel(**doc)


@router.delete("/{nid}")
async def delete_notification(nid: str, user=Depends(get_current_user)):
    r = await db.notification_channels.delete_one({"id": nid, "tenant_id": user["tenant_id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.post("/{nid}/test")
async def test_notification(nid: str, user=Depends(get_current_user)):
    ch = await db.notification_channels.find_one(
        {"id": nid, "tenant_id": user["tenant_id"]}, {"_id": 0}
    )
    if not ch:
        raise HTTPException(404)
    url = decrypt_url(ch["webhook_url"])
    fields = [("Sector", "Test"), ("Velocity", "+0%"), ("Z-Score", "0"), ("Confidence", "100%")]
    payload = slack_blocks("⚠️ TALK TO+ Test Alert", "This is a test message from TALK TO+ BDaaS.", fields) \
        if ch["type"] == "slack" else teams_card("TALK TO+ Test Alert", "Test message from TALK TO+ BDaaS.", fields)
    ok = await post_webhook(url, payload)
    if not ok:
        raise HTTPException(502, "Webhook delivery failed")
    return {"ok": True}
