"""
TALK TO+ BDaaS — Signal ingestion pipeline (used by REST + webhook).
"""
from core import db
from models import SignalStatus
from services.ai import analyze_signal_ai
from services.embedding import semantic_embed, cosine


async def analyze_and_store_signal(signal_id: str, tenant_id: str, content: str) -> None:
    """Compute embeddings, get top-3 strategy doc context via cosine, run AI analysis,
    persist results back to the signal document."""
    vec = semantic_embed(content)
    docs = await db.strategy_docs.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(100)
    ranked = []
    for d in docs:
        dv = d.get("vector") or semantic_embed(d["content"][:800])
        ranked.append((cosine(vec, dv), d["title"], d["content"][:400]))
    ranked.sort(reverse=True)
    ctx = "\n".join(f"- {t}: {c}" for _, t, c in ranked[:3])
    ai = await analyze_signal_ai(content, ctx)
    await db.signals.update_one(
        {"id": signal_id},
        {"$set": {
            "risk_level": ai["risk_level"],
            "confidence": ai["confidence"],
            "summary": ai["summary"],
            "execution_gaps": ai["execution_gaps"],
            "hidden_assumptions": ai["hidden_assumptions"],
            "facilitator_questions": ai["facilitator_questions"],
            "category": ai["category"],
            "semantic_vector": vec,
            "status": SignalStatus.PENDING.value,
        }},
    )
