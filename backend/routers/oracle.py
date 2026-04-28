"""Oracle alerts router — /api/oracle/*"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from fastapi import APIRouter, Depends

import numpy as np

from core import db, get_current_user
from models import OracleAlert, RiskLevel, RISK_WEIGHT
from services.embedding import ensure_aware

router = APIRouter(prefix="/oracle", tags=["oracle"])


@router.get("/alerts", response_model=List[OracleAlert])
async def oracle_alerts(user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    cutoff_recent = now - timedelta(hours=48)
    cutoff_prev = now - timedelta(hours=96)
    all_frags = await db.swarm_fragments.find({}, {"_id": 0}).to_list(10000)
    sectors: Dict[str, List[dict]] = {}
    for f in all_frags:
        f["created_at"] = ensure_aware(f.get("created_at"))
        sectors.setdefault(f.get("sector_display", "All"), []).append(f)

    alerts: List[OracleAlert] = []
    all_weights = [RISK_WEIGHT[RiskLevel(f["risk_level"])] for f in all_frags]
    mean = float(np.mean(all_weights)) if all_weights else 2.0
    std = float(np.std(all_weights)) if len(all_weights) > 1 else 1.0
    std = max(std, 0.1)

    for sector, frags in sectors.items():
        recent = [f for f in frags if f["created_at"] >= cutoff_recent]
        prev = [f for f in frags if cutoff_prev <= f["created_at"] < cutoff_recent]
        if not recent:
            continue
        r_cnt = len(recent)
        p_cnt = max(len(prev), 1)
        velocity = (r_cnt - p_cnt) / p_cnt * 100
        if velocity < 25 and r_cnt < 3:
            continue
        rw = [RISK_WEIGHT[RiskLevel(f["risk_level"])] for f in recent]
        sector_mean = float(np.mean(rw))
        z = (sector_mean - mean) / std
        conf = min(0.99, 0.5 + abs(z) * 0.15 + min(r_cnt, 20) / 40)
        sev = (
            RiskLevel.CRITICAL if z > 1.5 or velocity > 200 else
            RiskLevel.HIGH if z > 0.7 or velocity > 80 else
            RiskLevel.MODERATE
        )
        cats = {}
        for f in recent:
            cats[f["category"]] = cats.get(f["category"], 0) + 1
        dom = max(cats.items(), key=lambda x: x[1])[0]
        title = f"{dom.upper()} GAP SPIKE"
        desc_fi = f"Toimialalla havaittu {velocity:.0f}% kasvu {dom}-riskeissä viimeisen 48h aikana."
        alerts.append(OracleAlert(
            id=str(uuid.uuid4()),
            title=title, description=desc_fi,
            sector=sector,
            velocity=round(velocity, 1),
            z_score=round(z, 2),
            confidence=round(conf, 2),
            severity=sev,
            created_at=now,
        ))
    if all_frags:
        total_recent = sum(1 for f in all_frags if f["created_at"] >= cutoff_recent)
        total_prev = max(sum(1 for f in all_frags if cutoff_prev <= f["created_at"] < cutoff_recent), 1)
        macro_vel = (total_recent - total_prev) / total_prev * 100
        if macro_vel > 20:
            alerts.append(OracleAlert(
                id=str(uuid.uuid4()),
                title="GLOBAL MACRO TREND",
                description=f"Globaalit riskit kiihtyneet {macro_vel:.0f}% poikki kaikkien toimialojen.",
                sector="All Sectors",
                velocity=round(macro_vel, 1),
                z_score=round(abs(mean - 2) / std, 2),
                confidence=0.97,
                severity=RiskLevel.HIGH if macro_vel < 150 else RiskLevel.CRITICAL,
                created_at=now,
            ))
    alerts.sort(key=lambda a: a.velocity, reverse=True)
    return alerts[:6]
