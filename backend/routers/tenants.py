"""Tenants router — /api/tenants"""
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends

from core import db, get_current_user, require_role
from models import Tenant, TenantCreate, Role
from services.embedding import sector_hash

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=List[Tenant])
async def list_tenants(user=Depends(get_current_user)):
    docs = await db.tenants.find({}, {"_id": 0}).to_list(200)
    return [Tenant(**d) for d in docs]


@router.post("", response_model=Tenant)
async def create_tenant(body: TenantCreate, user=Depends(require_role(Role.SUPER_ADMIN))):
    tid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": tid, "name": body.name, "sector": body.sector,
        "sector_hash": sector_hash(body.sector),
        "description": body.description,
        "created_at": now, "active": True,
    }
    await db.tenants.insert_one(doc.copy())
    return Tenant(**doc)
