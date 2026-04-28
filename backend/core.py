"""
TALK TO+ BDaaS — Core: config, DB, auth, audit, rate limiter.
Shared across routers and services.
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pathlib import Path as FilePath

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

# --------------------------------------------------------------------
# Environment
# --------------------------------------------------------------------
ROOT = FilePath(__file__).parent
load_dotenv(ROOT / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]
JWT_EXPIRE_MINUTES = int(os.environ["JWT_EXPIRE_MINUTES"])
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
WEBHOOK_SECRET = os.environ["WEBHOOK_HMAC_SECRET"]

USE_LOCAL_LLM = os.environ.get("USE_LOCAL_LLM", "false").lower() == "true"
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "google/gemma-4b-it")
USE_POSTGRES = os.environ.get("USE_POSTGRES", "false").lower() == "true"
ENABLE_DISPATCHER = os.environ.get("ENABLE_DISPATCHER", "false").lower() == "true"
ENABLE_EMAIL_SCHEDULER = os.environ.get("ENABLE_EMAIL_SCHEDULER", "false").lower() == "true"
WEBHOOK_STRICT = os.environ.get("WEBHOOK_STRICT", "false").lower() == "true"
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "*")
CORS_ALLOW_LIST = [o.strip() for o in CORS_ORIGINS_RAW.split(",")] if CORS_ORIGINS_RAW != "*" else ["*"]
NOTIFICATION_FERNET_KEY = os.environ.get("NOTIFICATION_FERNET_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("talktoplus")

# --------------------------------------------------------------------
# DB / Mongo
# --------------------------------------------------------------------
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# --------------------------------------------------------------------
# Auth primitives
# --------------------------------------------------------------------
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)


def verify_password(pw: str, h: str) -> bool:
    try:
        return pwd_ctx.verify(pw, h)
    except Exception:
        return False


def create_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(token: Optional[str] = Depends(oauth2)) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = data.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles):
    async def checker(user=Depends(get_current_user)):
        role_values = [r.value if hasattr(r, "value") else r for r in roles]
        if user["role"] not in role_values:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


# --------------------------------------------------------------------
# Audit / Outbox
# --------------------------------------------------------------------
async def audit(event: str, user_id: Optional[str], tenant_id: Optional[str], payload: dict):
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "event": event,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "payload": payload,
        "created_at": datetime.now(timezone.utc),
        "delivered": False,
    })


# --------------------------------------------------------------------
# Rate limiter (shared)
# --------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)
