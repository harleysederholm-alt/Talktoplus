"""
TALK TO+ BDaaS — Email service (Resend) + monthly board-report dispatcher.
Gated entirely behind RESEND_API_KEY env. Silent no-op when missing.
"""
import os
import asyncio
import base64
from datetime import datetime, timezone
from typing import List, Optional

from core import db, logger

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")


def is_configured() -> bool:
    return bool(RESEND_API_KEY)


async def send_email_with_pdf(
    recipients: List[str],
    subject: str,
    html_body: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> dict:
    """Async-safe wrapper around the sync Resend SDK."""
    if not is_configured():
        return {"sent": False, "reason": "RESEND_API_KEY not configured"}
    if not recipients:
        return {"sent": False, "reason": "no recipients"}

    import resend
    resend.api_key = RESEND_API_KEY

    params = {
        "from": SENDER_EMAIL,
        "to": recipients,
        "subject": subject,
        "html": html_body,
        "attachments": [{
            "filename": pdf_filename,
            "content": base64.b64encode(pdf_bytes).decode("ascii"),
        }],
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        eid = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(f"Resend email sent to {len(recipients)} recipients (id={eid})")
        return {"sent": True, "id": eid, "recipients": recipients}
    except Exception as e:
        logger.exception(f"Resend send failed: {e}")
        return {"sent": False, "reason": str(e)}


# --------------------------------------------------------------------
# Monthly scheduler — last Friday of each month, 09:00 UTC
# --------------------------------------------------------------------
def _is_last_friday(now: datetime) -> bool:
    if now.weekday() != 4:  # 4 = Friday
        return False
    # next 7 days must move into next month → this is the last Friday
    from datetime import timedelta
    return (now + timedelta(days=7)).month != now.month


async def _send_for_tenant(tenant_id: str) -> Optional[dict]:
    """Generate and email the executive summary for one tenant."""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        return None
    sub = await db.email_subscriptions.find_one(
        {"tenant_id": tenant_id, "type": "monthly_board_report", "active": True},
        {"_id": 0},
    )
    if not sub or not sub.get("recipients"):
        return None

    # Build the report via the same router logic — keep it DRY
    from routers.reports import _build_executive_payload  # type: ignore
    from services.executive_report import render_executive_pdf

    payload = await _build_executive_payload(tenant_id, days=30)
    pdf_bytes = render_executive_pdf(payload)

    html = f"""
    <table style="font-family:Helvetica,sans-serif;color:#0A0A0A;max-width:560px;">
      <tr><td>
        <h2 style="margin:0 0 4px;font-size:22px;letter-spacing:-0.02em;">{payload['tenant_name']} — Monthly Board Report</h2>
        <div style="font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#64748B;">
          TALK TO+ BDaaS · {payload['window_label']}
        </div>
        <p style="font-size:14px;line-height:1.5;margin-top:14px;">{payload['headline']}</p>
        <p style="font-size:13px;line-height:1.55;color:#334155;">{payload['lede']}</p>
        <p style="font-size:12px;color:#64748B;margin-top:18px;">
          Global Risk Index: <strong>{payload['gri']['value']}</strong> ·
          Active HIGH+: <strong>{payload['gri']['active']}</strong> ·
          Swarm fragments: <strong>{payload['swarm_count']}</strong>
        </p>
        <p style="font-size:11px;color:#94A3B8;margin-top:24px;border-top:1px solid #E2E8F0;padding-top:8px;">
          Full PDF report attached. Confidential — Sovereign Edge.
        </p>
      </td></tr>
    </table>
    """
    fname = f"executive-summary-{tenant['name'].replace(' ', '_').lower()}-{datetime.now().strftime('%Y%m')}.pdf"
    res = await send_email_with_pdf(
        recipients=sub["recipients"],
        subject=f"📊 {tenant['name']} — Monthly Board Report",
        html_body=html,
        pdf_bytes=pdf_bytes,
        pdf_filename=fname,
    )
    await db.email_log.insert_one({
        "tenant_id": tenant_id,
        "type": "monthly_board_report",
        "recipients": sub["recipients"],
        "result": res,
        "sent_at": datetime.now(timezone.utc),
    })
    return res


async def monthly_scheduler_loop():
    """Tick every hour; fire on the last Friday at 09:00 UTC, only once per day."""
    last_run_date: Optional[str] = None
    while True:
        try:
            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")
            if (
                is_configured()
                and _is_last_friday(now)
                and now.hour == 9
                and last_run_date != today
            ):
                logger.info("Monthly board-report scheduler firing")
                tenants = await db.tenants.find({}, {"_id": 0, "id": 1}).to_list(500)
                for t in tenants:
                    await _send_for_tenant(t["id"])
                last_run_date = today
        except Exception:
            logger.exception("scheduler iteration failed")
        await asyncio.sleep(3600)
