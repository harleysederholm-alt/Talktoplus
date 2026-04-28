"""Auth router — /api/auth/*"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request

from core import db, hash_password, verify_password, create_token, get_current_user, limiter
from models import (
    UserPublic, LoginReq, RegisterReq, TokenResp, RoleSwitchReq, ProfileUpdateReq, Role,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResp)
async def register(body: RegisterReq):
    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(400, "Email already registered")
    tenant_id = body.tenant_id or "default-tenant"
    if not await db.tenants.find_one({"id": tenant_id}):
        tenant_id = "default-tenant"
    uid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.users.insert_one({
        "id": uid,
        "email": body.email.lower(),
        "full_name": body.full_name,
        "password_hash": hash_password(body.password),
        "role": Role.FACILITATOR.value,
        "tenant_id": tenant_id,
        "locale": "fi",
        "created_at": now,
    })
    user = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    return TokenResp(access_token=create_token(uid), user=UserPublic(**user))


@router.post("/login", response_model=TokenResp)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginReq):
    u = await db.users.find_one({"email": body.email.lower()})
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    pub = {k: v for k, v in u.items() if k not in ("_id", "password_hash")}
    return TokenResp(access_token=create_token(u["id"]), user=UserPublic(**pub))


@router.get("/me", response_model=UserPublic)
async def me(user=Depends(get_current_user)):
    return UserPublic(**user)


@router.post("/role", response_model=UserPublic)
async def switch_role(body: RoleSwitchReq, user=Depends(get_current_user)):
    """DEMO ONLY — allows the seeded admin user to switch role on the fly."""
    await db.users.update_one({"id": user["id"]}, {"$set": {"role": body.role.value}})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserPublic(**u)


@router.patch("/profile", response_model=UserPublic)
async def update_profile(body: ProfileUpdateReq, user=Depends(get_current_user)):
    upd = {}
    if body.full_name:
        upd["full_name"] = body.full_name
    if body.locale in ("fi", "en"):
        upd["locale"] = body.locale
    if body.notification_preferences is not None:
        upd["notification_preferences"] = body.notification_preferences
    if upd:
        await db.users.update_one({"id": user["id"]}, {"$set": upd})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserPublic(**u)
