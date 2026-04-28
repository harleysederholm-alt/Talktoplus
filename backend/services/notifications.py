"""
TALK TO+ BDaaS — Notification helpers (Slack / Teams) and outbox dispatcher.
"""
import json
import asyncio
from typing import List

from core import db, logger, NOTIFICATION_FERNET_KEY


def encrypt_url(url: str) -> str:
    """Optional encryption — Fernet if NOTIFICATION_FERNET_KEY set, else stored as-is."""
    if not NOTIFICATION_FERNET_KEY:
        return url
    try:
        from cryptography.fernet import Fernet
        return Fernet(NOTIFICATION_FERNET_KEY.encode()).encrypt(url.encode()).decode()
    except Exception:
        return url


def decrypt_url(stored: str) -> str:
    if not NOTIFICATION_FERNET_KEY:
        return stored
    try:
        from cryptography.fernet import Fernet
        return Fernet(NOTIFICATION_FERNET_KEY.encode()).decrypt(stored.encode()).decode()
    except Exception:
        return stored


def slack_blocks(title: str, description: str, fields: List[tuple]) -> dict:
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": title}},
            {"type": "section", "fields": [{"type": "mrkdwn", "text": f"*{k}:*\n{v}"} for k, v in fields]},
            {"type": "section", "text": {"type": "mrkdwn", "text": description}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "TALK TO+ BDaaS · Sovereign Edge"}]},
        ]
    }


def teams_card(title: str, description: str, fields: List[tuple]) -> dict:
    facts = [{"name": k, "value": str(v)} for k, v in fields]
    return {
        "@type": "MessageCard", "@context": "http://schema.org/extensions",
        "summary": title, "themeColor": "EF4444",
        "sections": [{"activityTitle": title, "facts": facts, "text": description}],
    }


async def post_webhook(url: str, payload: dict) -> bool:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, json=payload)
            return r.status_code < 400
    except Exception as e:
        logger.warning(f"notification post failed: {e}")
        return False


SEV_ORDER = {"LOW": 1, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}


async def dispatcher_loop():
    """Outbox dispatcher — processes audit_log entries delivered=False and pushes to channels."""
    NOTIFY_EVENTS = {"oracle.spike", "signal.validated"}
    while True:
        try:
            pending = await db.audit_log.find(
                {"delivered": False, "event": {"$in": list(NOTIFY_EVENTS)}}
            ).limit(50).to_list(50)
            for evt in pending:
                channels = await db.notification_channels.find(
                    {"tenant_id": evt["tenant_id"], "enabled": True}
                ).to_list(20)
                payload_data = evt.get("payload", {})
                severity = (payload_data.get("final_risk") or "HIGH").upper()
                for ch in channels:
                    min_sev = ch.get("min_severity", "HIGH")
                    if SEV_ORDER.get(severity, 0) < SEV_ORDER.get(min_sev, 3):
                        continue
                    fields = [(k, str(v)) for k, v in payload_data.items()][:6]
                    title = f"⚠️ {evt['event']} · {severity}"
                    desc = json.dumps(payload_data, ensure_ascii=False)[:300]
                    p = slack_blocks(title, desc, fields) if ch["type"] == "slack" else teams_card(title, desc, fields)
                    await post_webhook(decrypt_url(ch["webhook_url"]), p)
                await db.audit_log.update_one({"id": evt["id"]}, {"$set": {"delivered": True}})
        except Exception:
            logger.exception("dispatcher error")
        await asyncio.sleep(60)
