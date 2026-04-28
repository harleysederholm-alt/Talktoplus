"""Reports router — /api/reports/*"""
from datetime import datetime, timezone, timedelta
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr

from core import db, get_current_user, audit
from models import RiskLevel, RISK_WEIGHT
from services.embedding import ensure_aware, decay
from services.executive_report import render_executive_pdf
from services.drilldown_report import render_drilldown_pdf

router = APIRouter(prefix="/reports", tags=["reports"])

CATEGORY_LABELS = {
    "resources": "Resources",
    "capabilities": "Capabilities",
    "engagement": "Engagement",
    "process": "Process",
}
DIST_COLORS = {"CRITICAL": "#EF4444", "HIGH": "#F97316", "MODERATE": "#EAB308", "LOW": "#94A3B8"}


def _heatmap_label(avg: float, count: int) -> str:
    if count == 0: return "NONE"
    if avg >= 3.3: return "CRITICAL"
    if avg >= 2.4: return "HIGH"
    if avg >= 1.6: return "MODERATE"
    return "LOW"


# --------------------------------------------------------------------
# Executive summary PDF (also reused by monthly email scheduler)
# --------------------------------------------------------------------
async def _build_executive_payload(tenant_id: str, days: int) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    sigs = await db.signals.find(
        {"tenant_id": tenant_id, "status": {"$in": ["validated", "overridden"]}}, {"_id": 0},
    ).sort("validated_at", -1).to_list(2000)

    num = den = 0.0
    for s in sigs:
        rl = s.get("override_risk_level") or s["risk_level"]
        w = RISK_WEIGHT[RiskLevel(rl)]
        c = s.get("confidence") or 0.6
        t = ensure_aware(s.get("validated_at")) or now
        d = decay(t, now)
        num += w * c * d; den += c * d
    gri_value = round(num / den, 2) if den else 1.0
    active = sum(1 for s in sigs if RiskLevel(s.get("override_risk_level") or s["risk_level"]) in (RiskLevel.HIGH, RiskLevel.CRITICAL))

    trend = []
    for d in range(days - 1, -1, -1):
        pt = now - timedelta(days=d)
        n = de = 0.0
        for s in sigs:
            t = ensure_aware(s.get("validated_at"))
            if not t or t > pt:
                continue
            rl = s.get("override_risk_level") or s["risk_level"]
            w = RISK_WEIGHT[RiskLevel(rl)]
            c = s.get("confidence") or 0.6
            dec = decay(t, pt)
            n += w * c * dec; de += c * dec
        trend.append({"date": pt.strftime("%b %d"), "value": round(n / de, 2) if de else 1.0})

    cats = {k: [] for k in CATEGORY_LABELS}
    for s in sigs:
        c = s.get("category")
        if c in cats:
            rl = s.get("override_risk_level") or s["risk_level"]
            cats[c].append(RISK_WEIGHT[RiskLevel(rl)])
    heatmap = []
    for k, vals in cats.items():
        cnt = len(vals); avg = sum(vals) / cnt if cnt else 0.0
        heatmap.append({"label": CATEGORY_LABELS[k], "score": round(avg, 1), "level": _heatmap_label(avg, cnt), "count": cnt})

    counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for s in sigs:
        rl = s.get("override_risk_level") or s["risk_level"]
        if rl in counts: counts[rl] += 1
    total = sum(counts.values()) or 1
    distribution = [{"name": k, "value": v, "percentage": round(v / total * 100), "color": DIST_COLORS[k]} for k, v in counts.items()]

    alerts_raw = await db.swarm_fragments.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    sectors_recent = {}
    cutoff_recent = now - timedelta(hours=48)
    for f in alerts_raw:
        f["created_at"] = ensure_aware(f["created_at"])
        if f["created_at"] >= cutoff_recent:
            sectors_recent.setdefault(f.get("sector_display", "All"), []).append(f)
    alerts = []
    for sector, frags in sectors_recent.items():
        if len(frags) < 2:
            continue
        rw = [RISK_WEIGHT[RiskLevel(f["risk_level"])] for f in frags]
        avg = sum(rw) / len(rw)
        cats_ = {}
        for f in frags: cats_[f["category"]] = cats_.get(f["category"], 0) + 1
        dom = max(cats_.items(), key=lambda x: x[1])[0]
        sev = "CRITICAL" if avg >= 3.3 else "HIGH" if avg >= 2.4 else "MODERATE"
        alerts.append({
            "title": f"{dom.upper()} GAP SPIKE", "sector": sector, "severity": sev,
            "velocity": round(len(frags) * 100 / max(len(alerts_raw), 1), 0),
            "z_score": round(avg - 2.0, 2),
            "confidence": min(0.99, 0.55 + len(frags) / 30),
            "description": f"{len(frags)} fragments ({dom}) detected in {sector} during last 48h — sustained pressure on execution.",
        })
    alerts.sort(key=lambda a: a["severity"] == "CRITICAL", reverse=True)
    alerts = alerts[:3]

    in_window = [s for s in sigs if ensure_aware(s.get("validated_at") or s.get("submitted_at")) and ensure_aware(s.get("validated_at") or s.get("submitted_at")) >= cutoff]
    in_window.sort(key=lambda s: ensure_aware(s.get("validated_at") or s.get("submitted_at")) or now, reverse=True)
    top_signals = []
    for s in in_window[:6]:
        when = ensure_aware(s.get("validated_at") or s.get("submitted_at")) or now
        top_signals.append({
            "content_short": (s.get("summary") or s["content"])[:140] + ("…" if len(s.get("summary") or s["content"]) > 140 else ""),
            "business_unit": s.get("business_unit", "—"),
            "risk": s.get("override_risk_level") or s.get("risk_level") or "MODERATE",
            "when": when.strftime("%Y-%m-%d"),
        })

    cards = await db.action_cards.find({"tenant_id": tenant_id}, {"_id": 0, "swarm_verified": 1}).to_list(500)
    swarm_verified_count = sum(1 for c in cards if c.get("swarm_verified"))

    if gri_value >= 3.0:
        headline = "Execution risk elevated — board attention required."
        lede = (f"Global Risk Index sits at {gri_value} on a 0-4 scale. {active} of {len(sigs)} validated signals "
                f"are HIGH or CRITICAL. Sovereign Edge intelligence indicates concentrated pressure on "
                f"{', '.join([h['label'] for h in heatmap if h['level'] in ('HIGH', 'CRITICAL')]) or 'multiple categories'}. "
                "This report summarises top anomalies, recent validations, and recommended next steps.")
    elif gri_value >= 2.0:
        headline = "Execution holding — selective interventions required."
        lede = (f"Global Risk Index at {gri_value}, with {active} active HIGH+ items. "
                "Pressure remains concentrated; targeted facilitator action sufficient at this stage.")
    else:
        headline = "Execution stable — opportunity window for strategic bets."
        lede = (f"Global Risk Index at {gri_value}. {len(sigs)} signals validated in window. "
                "Conditions favorable for accelerating discretionary initiatives.")

    return {
        "tenant_name": (tenant or {}).get("name", "—"),
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "window_label": f"Last {days} days",
        "headline": headline, "lede": lede,
        "gri": {"value": gri_value, "trend": trend[-1]["value"] if trend else gri_value, "active": active, "total": len(sigs)},
        "swarm_count": await db.swarm_fragments.count_documents({}),
        "card_count": len(cards), "swarm_verified_count": swarm_verified_count,
        "trend": trend, "heatmap": heatmap, "distribution": distribution,
        "alerts": alerts, "signals": top_signals,
    }


@router.get("/executive-summary.pdf")
async def executive_summary_pdf(days: int = Query(30, ge=7, le=90), user=Depends(get_current_user)):
    payload = await _build_executive_payload(user["tenant_id"], days)
    pdf = render_executive_pdf(payload)
    await audit("report.exported", user["id"], user["tenant_id"], {"type": "executive_summary", "days": days})
    fname = f"executive-summary-{user['tenant_id'][:8]}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# --------------------------------------------------------------------
# Drill-down PDF for a single bottleneck category
# --------------------------------------------------------------------
DRILLDOWN_CONTENT = {
    "resources": {
        "explainer": ("Resource gap emerges when strategic targets exceed actual capacity. "
                      "It is the most common cross-organization execution blocker — historically 47% of all validated signals."),
        "why_it_matters": ("Execution timelines slip on average 38% when resource gap is discovered mid-project. "
                           "Early detection enables 60% faster recovery and protects committed delivery dates."),
        "playbook": [
            "Activate framework agreements with 1-2 capacity partners within 7 days of detection.",
            "Allocate a senior coach for a 30-day knowledge transfer overlap before the critical phase.",
            "Establish weekly burn-down metric reported to steering group.",
            "Define a binding go/no-go decision point at 4 weeks.",
            "Re-baseline customer commitments proactively if recovery does not begin within 3 weeks.",
        ],
        "related_sectors": ["Manufacturing", "Healthcare", "Financial Services", "Energy"],
    },
    "capabilities": {
        "explainer": ("Capability gap is a silent risk — often hidden until a critical system or process fails. "
                      "Approximately 28% of long-term execution risks stem from capability shortfalls."),
        "why_it_matters": ("Senior expertise leaving without successor pipeline causes an average 6-month productivity drop. "
                           "Targeted training investment yields 3.2x return when paired with mentor pairing."),
        "playbook": [
            "Skill-map the top-10 critical roles within 14 days.",
            "Launch mentor pairing for every senior expert with at least one apprentice.",
            "Stand up an LMS-based learning path measured every 90 days.",
            "Open a strategic hiring pipeline 12 months ahead of forecast attrition.",
            "Quarterly board review of capability KPIs and bench depth.",
        ],
        "related_sectors": ["Energy", "Healthcare", "Technology"],
    },
    "engagement": {
        "explainer": ("Engagement gap manifests as silent resistance in change initiatives. "
                      "Engagement below 50% predicts strategy failure with 73% probability."),
        "why_it_matters": ("Employee turnover is the most direct measure of engagement gap — every 1% rise in the "
                           "'concerned' segment predicts 0.4% turnover increase within 6 months."),
        "playbook": [
            "Run a pulse survey for 200 employees within 3 days.",
            "Publish a public response from leadership for the top-5 concerns.",
            "Hold a monthly Town Hall with livestream Q&A.",
            "Add engagement metrics to the HR quarterly board report.",
            "Deploy listening posts in three highest-risk business units.",
        ],
        "related_sectors": ["Manufacturing", "Financial Services", "Retail"],
    },
    "process": {
        "explainer": ("Process gap emerges when operations are not standardized at critical points or accountability is unclear. "
                      "Around 23% of all signals relate to process disruptions and ownership ambiguity."),
        "why_it_matters": ("Lack of a named owner causes an average 12-day decision delay. "
                           "Single clear owner appointment shortens the decision cycle by 70%."),
        "playbook": [
            "Appoint a C-level sponsor for every critical process within 5 days.",
            "Build a RACI matrix in 30 days with all stakeholders signed off.",
            "Define KPI metrics with weekly stand-ups and visible dashboards.",
            "Document the standard process in a single source of truth.",
            "Audit cycle quarterly with red-team review.",
        ],
        "related_sectors": ["Manufacturing", "Financial Services", "Energy & Marine"],
    },
}


@router.get("/drilldown/{category}.pdf")
async def drilldown_pdf(
    category: Literal["resources", "capabilities", "engagement", "process"],
    user=Depends(get_current_user),
):
    tid = user["tenant_id"]
    now = datetime.now(timezone.utc)
    tenant = await db.tenants.find_one({"id": tid}, {"_id": 0})

    # Tenant signals in this category
    sigs = await db.signals.find(
        {"tenant_id": tid, "category": category, "status": {"$in": ["validated", "overridden"]}},
        {"_id": 0},
    ).sort("validated_at", -1).to_list(200)

    weights = []
    tenant_signals = []
    for s in sigs:
        rl = s.get("override_risk_level") or s["risk_level"]
        weights.append(RISK_WEIGHT[RiskLevel(rl)])
        when = ensure_aware(s.get("validated_at") or s.get("submitted_at")) or now
        tenant_signals.append({
            "content": (s.get("summary") or s["content"])[:160] + ("…" if len(s.get("summary") or s["content"]) > 160 else ""),
            "business_unit": s.get("business_unit", "—"),
            "risk": rl,
            "when": when.strftime("%Y-%m-%d"),
        })
    tenant_avg_weight = round(sum(weights) / len(weights), 2) if weights else 0.0
    tenant_level = _heatmap_label(tenant_avg_weight, len(weights))

    # Cross-sector swarm view
    cutoff_recent = now - timedelta(hours=48)
    all_frags = await db.swarm_fragments.find({"category": category}, {"_id": 0}).to_list(5000)
    total_all = await db.swarm_fragments.count_documents({})
    by_sector = {}
    for f in all_frags:
        f["created_at"] = ensure_aware(f["created_at"])
        by_sector.setdefault(f.get("sector_display", "Unknown"), []).append(f)
    cross_sector = []
    for sector, frags in by_sector.items():
        rw = [RISK_WEIGHT[RiskLevel(f["risk_level"])] for f in frags]
        avg = sum(rw) / len(rw) if rw else 0.0
        sev = _heatmap_label(avg, len(rw))
        recent_cnt = sum(1 for f in frags if f["created_at"] >= cutoff_recent)
        velocity = round(recent_cnt * 100 / max(len(frags), 1), 0)
        cross_sector.append({
            "sector": sector, "count": len(frags),
            "severity": sev, "velocity": velocity,
        })
    cross_sector.sort(key=lambda r: r["count"], reverse=True)

    content = DRILLDOWN_CONTENT[category]
    payload = {
        "tenant_name": (tenant or {}).get("name", "—"),
        "category_label": CATEGORY_LABELS[category],
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "explainer": content["explainer"],
        "why_it_matters": content["why_it_matters"],
        "playbook": content["playbook"],
        "related_sectors": content["related_sectors"],
        "tenant_count": len(sigs),
        "tenant_avg_weight": tenant_avg_weight,
        "tenant_level": tenant_level,
        "swarm_count": len(all_frags),
        "swarm_pct": round(len(all_frags) * 100 / max(total_all, 1), 1),
        "sectors_count": len(by_sector),
        "tenant_signals": tenant_signals,
        "cross_sector": cross_sector,
    }
    pdf = render_drilldown_pdf(payload)
    await audit("report.exported", user["id"], tid, {"type": "drilldown", "category": category})
    fname = f"drilldown-{category}-{tid[:8]}-{now.strftime('%Y%m%d')}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# --------------------------------------------------------------------
# Email subscription management (monthly board report)
# --------------------------------------------------------------------
class SubscriptionUpsert(BaseModel):
    recipients: List[EmailStr]
    active: bool = True


@router.get("/subscriptions/monthly")
async def get_monthly_subscription(user=Depends(get_current_user)):
    from services.email import is_configured
    sub = await db.email_subscriptions.find_one(
        {"tenant_id": user["tenant_id"], "type": "monthly_board_report"},
        {"_id": 0},
    )
    return {
        "configured": is_configured(),
        "subscription": sub or {"recipients": [], "active": False, "type": "monthly_board_report"},
    }


@router.put("/subscriptions/monthly")
async def upsert_monthly_subscription(body: SubscriptionUpsert, user=Depends(get_current_user)):
    doc = {
        "tenant_id": user["tenant_id"],
        "type": "monthly_board_report",
        "recipients": [str(e) for e in body.recipients],
        "active": body.active,
        "updated_at": datetime.now(timezone.utc),
        "updated_by": user["id"],
    }
    await db.email_subscriptions.update_one(
        {"tenant_id": user["tenant_id"], "type": "monthly_board_report"},
        {"$set": doc},
        upsert=True,
    )
    await audit("subscription.updated", user["id"], user["tenant_id"], {"recipients": doc["recipients"], "active": body.active})
    return doc


@router.post("/subscriptions/monthly/test")
async def trigger_monthly_now(user=Depends(get_current_user)):
    """Manually fire the monthly send right now (admin/testing)."""
    from services.email import _send_for_tenant, is_configured
    if not is_configured():
        raise HTTPException(503, "RESEND_API_KEY not configured on backend")
    res = await _send_for_tenant(user["tenant_id"])
    if not res:
        raise HTTPException(404, "No active subscription with recipients")
    if not res.get("sent"):
        raise HTTPException(502, f"Send failed: {res.get('reason')}")
    return res
