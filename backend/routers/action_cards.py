"""Action Cards router — /api/action-cards/*"""
from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from core import db, get_current_user, audit
from models import ActionCard
from services.pdf import render_action_card_pdf

router = APIRouter(prefix="/action-cards", tags=["action-cards"])


@router.get("", response_model=List[ActionCard])
async def list_cards(user=Depends(get_current_user)):
    docs = await db.action_cards.find({"tenant_id": user["tenant_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [ActionCard(**d) for d in docs]


@router.post("/{cid}/impact", response_model=ActionCard)
async def score_card(cid: str, score: int, user=Depends(get_current_user)):
    if score < 1 or score > 10:
        raise HTTPException(400, "score 1-10")
    res = await db.action_cards.find_one_and_update(
        {"id": cid, "tenant_id": user["tenant_id"]},
        {"$set": {"impact_score": score}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(404, "Not found")
    return ActionCard(**res)


@router.post("/{cid}/status", response_model=ActionCard)
async def update_card_status(
    cid: str,
    status: Literal["pending_validation", "validated", "in_progress", "dismissed", "escalated"],
    user=Depends(get_current_user),
):
    res = await db.action_cards.find_one_and_update(
        {"id": cid, "tenant_id": user["tenant_id"]},
        {"$set": {"status": status}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(404, "Not found")
    await audit("card.status_changed", user["id"], user["tenant_id"], {"card_id": cid, "status": status})
    return ActionCard(**res)


@router.get("/{cid}/export.pdf")
async def export_card_pdf(cid: str, user=Depends(get_current_user)):
    card = await db.action_cards.find_one({"id": cid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not card:
        raise HTTPException(404)
    signal = await db.signals.find_one({"id": card["signal_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
    severity = (signal or {}).get("override_risk_level") or (signal or {}).get("risk_level") or "MODERATE"
    pdf_bytes = render_action_card_pdf(
        card=card, signal=signal, severity=severity,
        tenant_name=(tenant or {}).get("name", "—"),
    )
    await audit("card.exported", user["id"], user["tenant_id"], {"card_id": cid})
    return Response(
        pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="action-card-{cid[:8]}.pdf"'},
    )
