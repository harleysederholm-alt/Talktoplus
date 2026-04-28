"""Reports router — /api/reports/*"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from core import db, get_current_user, audit
from models import RiskLevel, RISK_WEIGHT
from services.embedding import ensure_aware, decay
from services.executive_report import render_executive_pdf

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


@router.get("/executive-summary.pdf")
async def executive_summary_pdf(
    days: int = Query(30, ge=7, le=90),
    user=Depends(get_current_user),
):
    """C-level quarterly board report PDF — GRI, trend, oracle, signals, heatmap, distribution."""
    tid = user["tenant_id"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    tenant = await db.tenants.find_one({"id": tid}, {"_id": 0})
    sigs = await db.signals.find(
        {"tenant_id": tid, "status": {"$in": ["validated", "overridden"]}},
        {"_id": 0},
    ).sort("validated_at", -1).to_list(2000)

    # GRI (full window)
    num = den = 0.0
    for s in sigs:
        rl = s.get("override_risk_level") or s["risk_level"]
        w = RISK_WEIGHT[RiskLevel(rl)]
        c = s.get("confidence") or 0.6
        t = ensure_aware(s.get("validated_at")) or now
        d = decay(t, now)
        num += w * c * d
        den += c * d
    gri_value = round(num / den, 2) if den else 1.0
    active = sum(1 for s in sigs if RiskLevel(s.get("override_risk_level") or s["risk_level"]) in (RiskLevel.HIGH, RiskLevel.CRITICAL))

    # Trend
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
        v = n / de if de else 1.0
        trend.append({"date": pt.strftime("%b %d"), "value": round(v, 2)})

    # Heatmap (4 categories)
    cats = {k: [] for k in CATEGORY_LABELS}
    for s in sigs:
        c = s.get("category")
        if c in cats:
            rl = s.get("override_risk_level") or s["risk_level"]
            cats[c].append(RISK_WEIGHT[RiskLevel(rl)])
    heatmap = []
    for k, vals in cats.items():
        cnt = len(vals)
        avg = sum(vals) / cnt if cnt else 0.0
        heatmap.append({"label": CATEGORY_LABELS[k], "score": round(avg, 1), "level": _heatmap_label(avg, cnt), "count": cnt})

    # Distribution
    counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for s in sigs:
        rl = s.get("override_risk_level") or s["risk_level"]
        if rl in counts:
            counts[rl] += 1
    total = sum(counts.values()) or 1
    distribution = [
        {"name": k, "value": v, "percentage": round(v / total * 100), "color": DIST_COLORS[k]}
        for k, v in counts.items()
    ]

    # Top 3 oracle alerts (cross-tenant signal — anonymized swarm view)
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
        for f in frags:
            cats_[f["category"]] = cats_.get(f["category"], 0) + 1
        dom = max(cats_.items(), key=lambda x: x[1])[0]
        sev = "CRITICAL" if avg >= 3.3 else "HIGH" if avg >= 2.4 else "MODERATE"
        alerts.append({
            "title": f"{dom.upper()} GAP SPIKE",
            "sector": sector,
            "severity": sev,
            "velocity": round(len(frags) * 100 / max(len(alerts_raw), 1), 0),
            "z_score": round(avg - 2.0, 2),
            "confidence": min(0.99, 0.55 + len(frags) / 30),
            "description": f"{len(frags)} fragments ({dom}) detected in {sector} during last 48h — sustained pressure on execution.",
        })
    alerts.sort(key=lambda a: a["severity"] == "CRITICAL", reverse=True)
    alerts = alerts[:3]

    # Top 5 recent validated signals in window
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

    # Card stats
    cards = await db.action_cards.find({"tenant_id": tid}, {"_id": 0, "swarm_verified": 1}).to_list(500)
    swarm_verified_count = sum(1 for c in cards if c.get("swarm_verified"))

    # Headline + lede
    if gri_value >= 3.0:
        headline = "Execution risk elevated — board attention required."
        lede = (
            f"Global Risk Index sits at {gri_value} on a 0-4 scale. {active} of {len(sigs)} validated signals "
            f"are HIGH or CRITICAL. Sovereign Edge intelligence indicates concentrated pressure on "
            f"{', '.join([h['label'] for h in heatmap if h['level'] in ('HIGH', 'CRITICAL')]) or 'multiple categories'}. "
            "This report summarises top anomalies, recent validations, and recommended next steps."
        )
    elif gri_value >= 2.0:
        headline = "Execution holding — selective interventions required."
        lede = (
            f"Global Risk Index at {gri_value}, with {active} active HIGH+ items. "
            "Pressure remains concentrated; targeted facilitator action sufficient at this stage."
        )
    else:
        headline = "Execution stable — opportunity window for strategic bets."
        lede = (
            f"Global Risk Index at {gri_value}. {len(sigs)} signals validated in window. "
            "Conditions favorable for accelerating discretionary initiatives."
        )

    payload = {
        "tenant_name": (tenant or {}).get("name", "—"),
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "window_label": f"Last {days} days",
        "headline": headline,
        "lede": lede,
        "gri": {"value": gri_value, "trend": trend[-1]["value"] if trend else gri_value, "active": active, "total": len(sigs)},
        "swarm_count": await db.swarm_fragments.count_documents({}),
        "card_count": len(cards),
        "swarm_verified_count": swarm_verified_count,
        "trend": trend,
        "heatmap": heatmap,
        "distribution": distribution,
        "alerts": alerts,
        "signals": top_signals,
    }

    pdf = render_executive_pdf(payload)
    await audit("report.exported", user["id"], tid, {"type": "executive_summary", "days": days})
    return Response(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="executive-summary-{tid[:8]}-{now.strftime("%Y%m%d")}.pdf"'},
    )
