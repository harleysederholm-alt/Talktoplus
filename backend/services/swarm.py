"""
TALK TO+ BDaaS — Swarm intelligence: pattern matching + cluster updates.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

import numpy as np

from core import db
from models import RiskLevel, RISK_WEIGHT
from services.embedding import cosine

CATEGORY_LABELS = {
    "resources": "Resurssivaje / Resource Gap",
    "capabilities": "Osaamisvaje / Capability Gap",
    "engagement": "Sitoutumisvaje / Engagement Gap",
    "process": "Prosessivaje / Process Gap",
}


async def query_universal_patterns(vec: List[float], tenant_id: str) -> List[str]:
    """Find success patterns (validated Action Cards from OTHER tenants) with high cosine."""
    if not vec:
        return []
    cards = await db.action_cards.find(
        {"tenant_id": {"$ne": tenant_id}, "impact_score": {"$gte": 4}},
        {"_id": 0}
    ).to_list(200)
    scored = []
    for c in cards:
        sig = await db.signals.find_one({"id": c["signal_id"]}, {"_id": 0, "semantic_vector": 1})
        if sig and sig.get("semantic_vector"):
            s = cosine(vec, sig["semantic_vector"])
            if s > 0.4:
                scored.append((s, c["summary"]))
    scored.sort(reverse=True)
    return [s for _, s in scored[:3]]


async def update_clusters():
    """Greedy cosine clustering of swarm fragments (threshold 0.55 for demo)."""
    frags = await db.swarm_fragments.find({}, {"_id": 0}).to_list(5000)
    if not frags:
        return
    THRESHOLD = 0.55
    clusters: List[Dict[str, Any]] = []
    for f in frags:
        v = f.get("semantic_vector") or []
        if not v:
            continue
        placed = False
        for cl in clusters:
            if cosine(v, cl["centroid"]) >= THRESHOLD and cl["category"] == f["category"]:
                cl["members"].append(f)
                cl["centroid"] = (np.array(cl["centroid"]) * (len(cl["members"]) - 1) + np.array(v)).tolist()
                n = np.linalg.norm(cl["centroid"])
                if n > 0:
                    cl["centroid"] = (np.array(cl["centroid"]) / n).tolist()
                placed = True
                break
        if not placed:
            clusters.append({"centroid": v, "category": f["category"], "members": [f]})

    total = sum(len(c["members"]) for c in clusters) or 1
    await db.universal_bottlenecks.delete_many({})
    now = datetime.now(timezone.utc)
    out = []
    for cl in clusters:
        if len(cl["members"]) < 1:
            continue
        sectors = list({m.get("sector_display", "Unknown") for m in cl["members"]})
        avg_w = sum(RISK_WEIGHT[RiskLevel(m["risk_level"])] for m in cl["members"]) / len(cl["members"])
        doc = {
            "id": str(uuid.uuid4()),
            "category": cl["category"],
            "label": CATEGORY_LABELS.get(cl["category"], cl["category"].title()),
            "fragment_count": len(cl["members"]),
            "percentage": round(len(cl["members"]) / total * 100, 1),
            "sectors_affected": sectors,
            "avg_risk_weight": round(avg_w, 2),
            "created_at": now,
        }
        out.append(doc)
    if out:
        await db.universal_bottlenecks.insert_many([d.copy() for d in out])
