"""Analytics router — /api/analytics/*"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends

from core import db, get_current_user
from models import RiskLevel, RISK_WEIGHT
from services.embedding import ensure_aware, decay

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/global-risk-index")
async def global_risk_index(user=Depends(get_current_user)):
    """R_global = Σ(W*C*e^-λt) / Σ(C*e^-λt) over validated signals in tenant."""
    now = datetime.now(timezone.utc)
    signals = await db.signals.find(
        {"tenant_id": user["tenant_id"], "status": {"$in": ["validated", "overridden"]}},
        {"_id": 0, "risk_level": 1, "confidence": 1, "validated_at": 1, "override_risk_level": 1},
    ).to_list(2000)
    if not signals:
        return {"value": 1.0, "trend": "stable", "active": 0, "total": 0}
    num = 0.0; den = 0.0
    for s in signals:
        rl = s.get("override_risk_level") or s["risk_level"]
        w = RISK_WEIGHT[RiskLevel(rl)]
        c = s.get("confidence") or 0.6
        t = ensure_aware(s.get("validated_at")) or now
        d = decay(t, now)
        num += w * c * d
        den += c * d
    val = num / den if den else 1.0

    cutoff = now - timedelta(hours=24)
    recent = [s for s in signals if (ensure_aware(s.get("validated_at")) or now) >= cutoff]
    trend = "stable"
    if len(recent) >= 3:
        r_num = r_den = 0.0
        for s in recent:
            rl = s.get("override_risk_level") or s["risk_level"]
            w = RISK_WEIGHT[RiskLevel(rl)]
            c = s.get("confidence") or 0.6
            d = decay(ensure_aware(s.get("validated_at")) or now, now)
            r_num += w * c * d; r_den += c * d
        r_val = r_num / r_den if r_den else val
        if r_val > val * 1.1:
            trend = "rising"
        elif r_val < val * 0.9:
            trend = "falling"
    return {
        "value": round(val, 2),
        "trend": trend,
        "active": sum(1 for s in signals if RiskLevel(s.get("override_risk_level") or s["risk_level"]) in (RiskLevel.HIGH, RiskLevel.CRITICAL)),
        "total": len(signals),
    }


@router.get("/risk-trend")
async def risk_trend(days: int = 7, user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    out = []
    all_sigs = await db.signals.find(
        {"tenant_id": user["tenant_id"], "status": {"$in": ["validated", "overridden"]}},
        {"_id": 0, "risk_level": 1, "confidence": 1, "validated_at": 1, "override_risk_level": 1},
    ).to_list(5000)
    for d in range(days - 1, -1, -1):
        point_time = now - timedelta(days=d)
        num = den = 0.0
        for s in all_sigs:
            t = ensure_aware(s.get("validated_at"))
            if not t or t > point_time:
                continue
            rl = s.get("override_risk_level") or s["risk_level"]
            w = RISK_WEIGHT[RiskLevel(rl)]
            c = s.get("confidence") or 0.6
            dec = decay(t, point_time)
            num += w * c * dec; den += c * dec
        v = num / den if den else 1.0
        out.append({"date": point_time.strftime("%b %d"), "value": round(v, 2)})
    return out


@router.get("/heatmap")
async def heatmap(user=Depends(get_current_user)):
    """Four buckets: resources / capabilities / engagement / process — avg risk weight."""
    sigs = await db.signals.find(
        {"tenant_id": user["tenant_id"], "status": {"$in": ["validated", "overridden"]}, "category": {"$ne": None}},
        {"_id": 0, "category": 1, "risk_level": 1, "override_risk_level": 1},
    ).to_list(5000)
    cats = {"resources": [], "capabilities": [], "engagement": [], "process": []}
    for s in sigs:
        c = s.get("category")
        if c in cats:
            rl = s.get("override_risk_level") or s["risk_level"]
            cats[c].append(RISK_WEIGHT[RiskLevel(rl)])

    def label(avg, count):
        if count == 0: return "NONE"
        if avg >= 3.3: return "CRITICAL"
        if avg >= 2.4: return "HIGH"
        if avg >= 1.6: return "MODERATE"
        return "LOW"

    out = {}
    for k, vals in cats.items():
        cnt = len(vals)
        avg = sum(vals) / cnt if cnt else 0.0
        out[k] = {"score": round(avg, 1), "level": label(avg, cnt), "count": cnt}
    return out


@router.get("/distribution")
async def distribution(user=Depends(get_current_user)):
    sigs = await db.signals.find(
        {"tenant_id": user["tenant_id"], "status": {"$in": ["validated", "overridden"]}},
        {"_id": 0, "risk_level": 1, "override_risk_level": 1},
    ).to_list(5000)
    counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for s in sigs:
        rl = s.get("override_risk_level") or s["risk_level"]
        if rl in counts:
            counts[rl] += 1
    total = sum(counts.values()) or 1
    return [
        {"name": k, "value": v, "percentage": round(v / total * 100)}
        for k, v in counts.items()
    ]
