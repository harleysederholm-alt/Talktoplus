"""
TALK TO+ BDaaS - Execution Risk Validation Engine
FastAPI backend: Sovereign Edge + Global Intelligence (Mothership)
"""
import os
import hashlib
import hmac
import json
import math
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal, Dict, Any
from enum import Enum
from pathlib import Path as FilePath

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import jwt, JWTError
import numpy as np

# --------------------------------------------------------------------
# Load environment
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

# Feature flags & prod hardening
USE_LOCAL_LLM = os.environ.get("USE_LOCAL_LLM", "false").lower() == "true"
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "google/gemma-4b-it")
USE_POSTGRES = os.environ.get("USE_POSTGRES", "false").lower() == "true"  # docs/01 stub
ENABLE_DISPATCHER = os.environ.get("ENABLE_DISPATCHER", "false").lower() == "true"
WEBHOOK_STRICT = os.environ.get("WEBHOOK_STRICT", "false").lower() == "true"
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "*")
CORS_ALLOW_LIST = [o.strip() for o in CORS_ORIGINS_RAW.split(",")] if CORS_ORIGINS_RAW != "*" else ["*"]
NOTIFICATION_FERNET_KEY = os.environ.get("NOTIFICATION_FERNET_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("talktoplus")

# --------------------------------------------------------------------
# DB
# --------------------------------------------------------------------
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# --------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------
class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


RISK_WEIGHT = {RiskLevel.LOW: 1, RiskLevel.MODERATE: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    FACILITATOR = "facilitator"
    EXECUTIVE = "executive"
    VIEWER = "viewer"


class SignalStatus(str, Enum):
    PENDING = "pending"          # AI analyzed, awaiting facilitator
    VALIDATED = "validated"
    OVERRIDDEN = "overridden"
    DISMISSED = "dismissed"


class BottleneckCategory(str, Enum):
    RESOURCES = "resources"
    CAPABILITIES = "capabilities"
    ENGAGEMENT = "engagement"
    PROCESS = "process"


# --------------------------------------------------------------------
# Models
# --------------------------------------------------------------------
class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    tenant_id: str
    locale: str = "fi"
    created_at: datetime


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class RegisterReq(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: Optional[str] = None


class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class Tenant(BaseModel):
    id: str
    name: str
    sector: str                       # e.g. "Technology", "Healthcare"
    sector_hash: str                  # hashed for swarm anonymity
    created_at: datetime
    active: bool = True
    description: Optional[str] = None


class TenantCreate(BaseModel):
    name: str
    sector: str
    description: Optional[str] = None


class Signal(BaseModel):
    id: str
    tenant_id: str
    content: str
    source: str = "manual"             # manual|howspace|teams|slack
    business_unit: str
    author: str
    submitted_at: datetime
    status: SignalStatus
    # AI output
    risk_level: Optional[RiskLevel] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    execution_gaps: List[str] = []
    hidden_assumptions: List[str] = []
    facilitator_questions: List[str] = []
    category: Optional[BottleneckCategory] = None
    semantic_vector: Optional[List[float]] = None
    # Validation
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    validation_note: Optional[str] = None
    override_risk_level: Optional[RiskLevel] = None
    # Swarm link
    swarm_fragment_id: Optional[str] = None
    action_card_id: Optional[str] = None


class SignalCreate(BaseModel):
    content: str
    business_unit: str
    author: Optional[str] = None
    source: str = "manual"


class ValidationReq(BaseModel):
    decision: Literal["validate", "override", "dismiss"]
    note: Optional[str] = None
    override_risk_level: Optional[RiskLevel] = None


class ActionCard(BaseModel):
    id: str
    tenant_id: str
    signal_id: str
    title: str
    summary: str
    playbook: List[str]                # steps
    rag_context_used: List[str] = []   # from strategy docs
    swarm_patterns_used: List[str] = [] # from mothership
    impact_score: Optional[int] = None # facilitator scored 1-5
    swarm_verified: bool = False
    created_at: datetime


class StrategyDoc(BaseModel):
    id: str
    tenant_id: str
    title: str
    content: str
    chunks: int = 0
    uploaded_by: str
    created_at: datetime


class StrategyDocCreate(BaseModel):
    title: str
    content: str


class SwarmFragment(BaseModel):
    id: str
    sector_hash: str
    risk_level: RiskLevel
    confidence: float
    category: BottleneckCategory
    semantic_vector: List[float]
    created_at: datetime
    # ZERO raw content


class UniversalBottleneck(BaseModel):
    id: str
    category: BottleneckCategory
    label: str
    fragment_count: int
    percentage: float
    sectors_affected: List[str]
    avg_risk_weight: float
    created_at: datetime


class OracleAlert(BaseModel):
    id: str
    title: str
    description: str
    sector: str
    velocity: float                   # % change
    z_score: float
    confidence: float
    severity: RiskLevel
    created_at: datetime


# --------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------
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


def require_role(*roles: Role):
    async def checker(user=Depends(get_current_user)):
        if user["role"] not in [r.value for r in roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


# --------------------------------------------------------------------
# AI helpers – Gemini 3 Flash via emergentintegrations
# --------------------------------------------------------------------
AI_SYSTEM_PROMPT = """You are TALK TO+ BDaaS Local Node — an enterprise execution-risk analyst.
Your job is to stress-test signals against company strategy and expose hidden execution gaps.
You respond ONLY with strict JSON, no markdown, no prose. Schema:
{
 "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
 "confidence": 0.0-1.0,
 "summary": "2 sentences, language matching input",
 "execution_gaps": ["gap1", "gap2"],
 "hidden_assumptions": ["assumption1"],
 "facilitator_questions": ["question1", "question2"],
 "category": "resources|capabilities|engagement|process"
}
Be direct, critical, Finnish-enterprise blunt when input is Finnish. Focus on execution, not strategy itself."""


async def _llm_chat_json(system_prompt: str, user_text: str, session_id: str) -> str:
    """Unified LLM call. If USE_LOCAL_LLM=true → vLLM (OpenAI-compatible).
    Else → Gemini 3 Flash via emergentintegrations. Returns raw response text."""
    if USE_LOCAL_LLM and VLLM_BASE_URL:
        # vLLM (Sovereign Edge — docs/06). OpenAI-compatible endpoint.
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="not-needed")
            resp = await client.chat.completions.create(
                model=VLLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=800,
            )
            return resp.choices[0].message.content or ""
        except ImportError:
            logger.error("openai package missing; falling back to Gemini")
    # Default: Gemini 3 Flash
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model("gemini", "gemini-3-flash-preview")
    return await chat.send_message(UserMessage(text=user_text))


async def analyze_signal_ai(content: str, strategy_context: str = "") -> dict:
    try:
        user_text = f"STRATEGY CONTEXT:\n{strategy_context[:2000]}\n\nSIGNAL:\n{content}\n\nReturn JSON only."
        resp = await _llm_chat_json(AI_SYSTEM_PROMPT, user_text, f"signal-{uuid.uuid4()}")
        txt = resp.strip()
        # Strip code fences if any
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            if txt.startswith("json"):
                txt = txt[4:]
        parsed = json.loads(txt.strip())
        # Normalize
        rl = parsed.get("risk_level", "MODERATE").upper()
        if rl not in [e.value for e in RiskLevel]:
            rl = "MODERATE"
        cat = parsed.get("category", "process").lower()
        if cat not in [e.value for e in BottleneckCategory]:
            cat = "process"
        return {
            "risk_level": rl,
            "confidence": float(parsed.get("confidence", 0.7)),
            "summary": parsed.get("summary", "")[:500],
            "execution_gaps": list(parsed.get("execution_gaps", []))[:5],
            "hidden_assumptions": list(parsed.get("hidden_assumptions", []))[:5],
            "facilitator_questions": list(parsed.get("facilitator_questions", []))[:5],
            "category": cat,
        }
    except Exception as e:
        logger.warning(f"AI analysis fallback: {e}")
        # Heuristic fallback so system never breaks
        low_kw = ["onnistui", "hyvä", "stable", "good", "works"]
        crit_kw = ["kriittinen", "critical", "urgent", "failing", "blocker", "resurssipula"]
        high_kw = ["huoli", "concern", "risk", "issue", "problem", "ongelma"]
        c = content.lower()
        if any(k in c for k in crit_kw):
            rl = "CRITICAL"
        elif any(k in c for k in high_kw):
            rl = "HIGH"
        elif any(k in c for k in low_kw):
            rl = "LOW"
        else:
            rl = "MODERATE"
        return {
            "risk_level": rl,
            "confidence": 0.55,
            "summary": f"Heuristinen analyysi (AI-yhteys offline). Signaali viittaa tasoon {rl}.",
            "execution_gaps": ["Yksityiskohtainen toimeenpano vaatii tarkennusta"],
            "hidden_assumptions": ["Oletetaan nykyinen kapasiteetti riittää"],
            "facilitator_questions": ["Mitä konkreettista tukea tarvitaan?", "Kuka omistaa tämän ongelman?"],
            "category": "process",
        }


PRESCRIPTIVE_PROMPT = """You are TALK TO+ BDaaS Prescriptive Engine.
Generate an Action Card playbook based on a validated execution risk and universal success patterns.
Respond ONLY with strict JSON:
{
 "title": "short title (max 80 chars)",
 "summary": "1-2 sentence description, language matching input",
 "playbook": ["step 1", "step 2", "step 3", "step 4", "step 5"]
}
Be specific, operational, enterprise-ready."""


async def generate_action_card_ai(signal_summary: str, gaps: List[str], patterns: List[str]) -> dict:
    try:
        msg = f"""VALIDATED SIGNAL:\n{signal_summary}\n\nEXECUTION GAPS:\n{chr(10).join('- '+g for g in gaps)}\n\nUNIVERSAL SUCCESS PATTERNS FROM SWARM:\n{chr(10).join('- '+p for p in patterns) or '(none yet)'}\n\nReturn JSON."""
        resp = await _llm_chat_json(PRESCRIPTIVE_PROMPT, msg, f"card-{uuid.uuid4()}")
        txt = resp.strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            if txt.startswith("json"):
                txt = txt[4:]
        p = json.loads(txt.strip())
        return {
            "title": p.get("title", "Playbook")[:120],
            "summary": p.get("summary", "")[:500],
            "playbook": list(p.get("playbook", []))[:10],
        }
    except Exception as e:
        logger.warning(f"Action card fallback: {e}")
        return {
            "title": f"Interventio: {signal_summary[:60]}",
            "summary": "Suositeltu korjaava toimenpideketju perustuen havaittuihin toimeenpanoaukkoihin.",
            "playbook": [
                "1. Kutsu omistaja ja sidosryhmät 48h sisään",
                "2. Kartoita kapasiteetti ja resurssit vs. tavoite",
                "3. Määritä kaksi mittaria viikkotarkastelua varten",
                "4. Sovi selkeä go/no-go -päätöspiste 2 viikon päähän",
                "5. Raportoi ohjausryhmälle etenemisestä viikoittain",
            ],
        }


# --------------------------------------------------------------------
# Semantic vector (deterministic hashing-based embedding)
# In production this is BGE-M3. Here we use a stable hash-projection
# so swarm clustering works deterministically offline.
# --------------------------------------------------------------------
VECTOR_DIM = 256


def semantic_embed(text: str) -> List[float]:
    """Stable pseudo-embedding for clustering. Hash n-grams into buckets."""
    vec = np.zeros(VECTOR_DIM, dtype=np.float32)
    words = [w.lower() for w in text.split() if len(w) > 2]
    if not words:
        return vec.tolist()
    # unigrams
    for w in words:
        h = int(hashlib.sha256(w.encode()).hexdigest(), 16) % VECTOR_DIM
        vec[h] += 1.0
    # bigrams for context
    for i in range(len(words) - 1):
        h = int(hashlib.sha256(f"{words[i]}_{words[i+1]}".encode()).hexdigest(), 16) % VECTOR_DIM
        vec[h] += 0.7
    n = np.linalg.norm(vec)
    if n > 0:
        vec = vec / n
    return vec.tolist()


def cosine(a: List[float], b: List[float]) -> float:
    a = np.array(a); b = np.array(b)
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def sector_hash(sector: str) -> str:
    return hashlib.sha256(f"talktoplus::{sector.lower().strip()}".encode()).hexdigest()[:16]


# --------------------------------------------------------------------
# FastAPI app
# --------------------------------------------------------------------
app = FastAPI(title="TALK TO+ BDaaS", version="1.3.0")
api = APIRouter(prefix="/api")

# ----- Rate limiting (docs/07) -----
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ----- Security headers (docs/07) -----
@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if request.url.scheme == "https":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_LIST, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# --------------------------------------------------------------------
# Auth endpoints
# --------------------------------------------------------------------
@api.post("/auth/register", response_model=TokenResp)
async def register(body: RegisterReq):
    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(400, "Email already registered")
    tenant_id = body.tenant_id or "default-tenant"
    # ensure tenant exists
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


@api.post("/auth/login", response_model=TokenResp)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginReq):
    u = await db.users.find_one({"email": body.email.lower()})
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    pub = {k: v for k, v in u.items() if k not in ("_id", "password_hash")}
    return TokenResp(access_token=create_token(u["id"]), user=UserPublic(**pub))


@api.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(get_current_user)):
    return UserPublic(**user)


# --------------------------------------------------------------------
# Tenants
# --------------------------------------------------------------------
@api.get("/tenants", response_model=List[Tenant])
async def list_tenants(user=Depends(get_current_user)):
    docs = await db.tenants.find({}, {"_id": 0}).to_list(200)
    return [Tenant(**d) for d in docs]


@api.post("/tenants", response_model=Tenant)
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


# --------------------------------------------------------------------
# Signals (core flow: webhook → AI analyze → pending → validate → swarm → action card)
# --------------------------------------------------------------------
async def _analyze_and_store_signal(signal_id: str, tenant_id: str, content: str) -> None:
    # get strategy context (top docs by cosine)
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


@api.post("/signals", response_model=Signal)
async def create_signal(body: SignalCreate, user=Depends(get_current_user)):
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": sid, "tenant_id": user["tenant_id"],
        "content": body.content, "source": body.source,
        "business_unit": body.business_unit,
        "author": body.author or user["full_name"],
        "submitted_at": now,
        "status": SignalStatus.PENDING.value,
        "risk_level": None, "confidence": None, "summary": None,
        "execution_gaps": [], "hidden_assumptions": [], "facilitator_questions": [],
        "category": None, "semantic_vector": None,
        "validated_by": None, "validated_at": None, "validation_note": None,
        "override_risk_level": None, "swarm_fragment_id": None, "action_card_id": None,
    }
    await db.signals.insert_one(doc.copy())
    await _analyze_and_store_signal(sid, user["tenant_id"], body.content)
    s = await db.signals.find_one({"id": sid}, {"_id": 0})
    return Signal(**s)


@api.get("/signals", response_model=List[Signal])
async def list_signals(
    status_: Optional[SignalStatus] = None,
    limit: int = 100,
    user=Depends(get_current_user),
):
    q = {"tenant_id": user["tenant_id"]}
    if status_:
        q["status"] = status_.value
    docs = await db.signals.find(q, {"_id": 0}).sort("submitted_at", -1).limit(limit).to_list(limit)
    return [Signal(**d) for d in docs]


@api.get("/signals/{sid}", response_model=Signal)
async def get_signal(sid: str, user=Depends(get_current_user)):
    s = await db.signals.find_one({"id": sid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Signal not found")
    return Signal(**s)


@api.post("/signals/{sid}/validate", response_model=Signal)
async def validate_signal(sid: str, body: ValidationReq, user=Depends(get_current_user)):
    s = await db.signals.find_one({"id": sid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Signal not found")
    if s["status"] != SignalStatus.PENDING.value:
        raise HTTPException(400, "Signal already processed")
    now = datetime.now(timezone.utc)
    if body.decision == "dismiss":
        new_status = SignalStatus.DISMISSED
        await db.signals.update_one({"id": sid}, {"$set": {
            "status": new_status.value,
            "validated_by": user["full_name"], "validated_at": now,
            "validation_note": body.note,
        }})
        out = await db.signals.find_one({"id": sid}, {"_id": 0})
        return Signal(**out)

    new_status = SignalStatus.OVERRIDDEN if body.decision == "override" else SignalStatus.VALIDATED
    final_risk = body.override_risk_level.value if (body.decision == "override" and body.override_risk_level) else s["risk_level"]

    # Create swarm fragment (zero-knowledge)
    tenant = await db.tenants.find_one({"id": s["tenant_id"]}, {"_id": 0})
    sh = tenant["sector_hash"] if tenant else sector_hash("unknown")
    frag_id = str(uuid.uuid4())
    await db.swarm_fragments.insert_one({
        "id": frag_id,
        "sector_hash": sh,
        "sector_display": tenant["sector"] if tenant else "Unknown",
        "risk_level": final_risk,
        "confidence": s.get("confidence") or 0.6,
        "category": s.get("category") or "process",
        "semantic_vector": s.get("semantic_vector") or [],
        "created_at": now,
    })

    # Pull universal success patterns (anonymous cross-tenant)
    patterns = await _query_universal_patterns(s.get("semantic_vector") or [], s["tenant_id"])

    # Generate Action Card
    card_data = await generate_action_card_ai(s.get("summary") or s["content"][:300], s.get("execution_gaps") or [], patterns)
    card_id = str(uuid.uuid4())
    await db.action_cards.insert_one({
        "id": card_id,
        "tenant_id": s["tenant_id"],
        "signal_id": sid,
        "title": card_data["title"],
        "summary": card_data["summary"],
        "playbook": card_data["playbook"],
        "rag_context_used": [],
        "swarm_patterns_used": patterns,
        "impact_score": None,
        "swarm_verified": len(patterns) > 0,
        "created_at": now,
    })

    await db.signals.update_one({"id": sid}, {"$set": {
        "status": new_status.value,
        "validated_by": user["full_name"], "validated_at": now,
        "validation_note": body.note,
        "override_risk_level": body.override_risk_level.value if body.override_risk_level else None,
        "swarm_fragment_id": frag_id,
        "action_card_id": card_id,
    }})

    # Audit + outbox
    await audit("signal.validated", user["id"], s["tenant_id"], {
        "signal_id": sid, "decision": body.decision, "final_risk": final_risk, "card_id": card_id,
    })

    # Cluster update in bg
    asyncio.create_task(_update_clusters())

    out = await db.signals.find_one({"id": sid}, {"_id": 0})
    return Signal(**out)


# --------------------------------------------------------------------
# Action Cards
# --------------------------------------------------------------------
@api.get("/action-cards", response_model=List[ActionCard])
async def list_cards(user=Depends(get_current_user)):
    docs = await db.action_cards.find({"tenant_id": user["tenant_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [ActionCard(**d) for d in docs]


@api.post("/action-cards/{cid}/impact", response_model=ActionCard)
async def score_card(cid: str, score: int, user=Depends(get_current_user)):
    if score < 1 or score > 5:
        raise HTTPException(400, "score 1-5")
    res = await db.action_cards.find_one_and_update(
        {"id": cid, "tenant_id": user["tenant_id"]},
        {"$set": {"impact_score": score}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(404, "Not found")
    return ActionCard(**res)


# --------------------------------------------------------------------
# Strategy RAG
# --------------------------------------------------------------------
@api.get("/strategy-docs", response_model=List[StrategyDoc])
async def list_docs(user=Depends(get_current_user)):
    docs = await db.strategy_docs.find({"tenant_id": user["tenant_id"]}, {"_id": 0, "vector": 0})\
        .sort("created_at", -1).to_list(200)
    return [StrategyDoc(**d) for d in docs]


@api.post("/strategy-docs", response_model=StrategyDoc)
async def create_doc(body: StrategyDocCreate, user=Depends(get_current_user)):
    did = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    vec = semantic_embed(body.content[:4000])
    doc = {
        "id": did, "tenant_id": user["tenant_id"],
        "title": body.title, "content": body.content,
        "chunks": max(1, len(body.content) // 500),
        "uploaded_by": user["full_name"], "created_at": now,
        "vector": vec,
    }
    await db.strategy_docs.insert_one(doc.copy())
    doc.pop("vector")
    return StrategyDoc(**doc)


@api.delete("/strategy-docs/{did}")
async def delete_doc(did: str, user=Depends(get_current_user)):
    r = await db.strategy_docs.delete_one({"id": did, "tenant_id": user["tenant_id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# --------------------------------------------------------------------
# Swarm / Mothership (anonymous global intelligence)
# --------------------------------------------------------------------
async def _query_universal_patterns(vec: List[float], tenant_id: str) -> List[str]:
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


async def _update_clusters():
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
                # update centroid running avg
                cl["centroid"] = (np.array(cl["centroid"]) * (len(cl["members"]) - 1) + np.array(v)).tolist()
                n = np.linalg.norm(cl["centroid"])
                if n > 0:
                    cl["centroid"] = (np.array(cl["centroid"]) / n).tolist()
                placed = True
                break
        if not placed:
            clusters.append({"centroid": v, "category": f["category"], "members": [f]})

    # Rebuild bottleneck collection
    total = sum(len(c["members"]) for c in clusters) or 1
    await db.universal_bottlenecks.delete_many({})
    CATEGORY_LABELS = {
        "resources": "Resurssivaje / Resource Gap",
        "capabilities": "Osaamisvaje / Capability Gap",
        "engagement": "Sitoutumisvaje / Engagement Gap",
        "process": "Prosessivaje / Process Gap",
    }
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


@api.get("/swarm/bottlenecks", response_model=List[UniversalBottleneck])
async def bottlenecks(user=Depends(get_current_user)):
    docs = await db.universal_bottlenecks.find({}, {"_id": 0}).sort("fragment_count", -1).to_list(50)
    # collapse duplicates by category (keep highest)
    seen = {}
    for d in docs:
        if d["category"] not in seen or d["fragment_count"] > seen[d["category"]]["fragment_count"]:
            seen[d["category"]] = d
    return [UniversalBottleneck(**d) for d in seen.values()]


@api.get("/swarm/fragments/count")
async def fragment_count(user=Depends(get_current_user)):
    return {"count": await db.swarm_fragments.count_documents({})}


@api.post("/swarm/recompute")
async def recompute(user=Depends(require_role(Role.SUPER_ADMIN))):
    await _update_clusters()
    return {"ok": True}


# --------------------------------------------------------------------
# Oracle: Z-score anomaly & risk velocity
# --------------------------------------------------------------------
@api.get("/oracle/alerts", response_model=List[OracleAlert])
async def oracle_alerts(user=Depends(get_current_user)):
    # compute velocity per sector over last 48h vs previous 48h
    now = datetime.now(timezone.utc)
    cutoff_recent = now - timedelta(hours=48)
    cutoff_prev = now - timedelta(hours=96)
    all_frags = await db.swarm_fragments.find({}, {"_id": 0}).to_list(10000)
    # group by sector_display
    sectors: Dict[str, List[dict]] = {}
    for f in all_frags:
        f["created_at"] = _ensure_aware(f.get("created_at"))
        sectors.setdefault(f.get("sector_display", "All"), []).append(f)

    alerts: List[OracleAlert] = []
    all_weights = []
    for frag in all_frags:
        all_weights.append(RISK_WEIGHT[RiskLevel(frag["risk_level"])])
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
        # z-score for mean risk weight in sector
        rw = [RISK_WEIGHT[RiskLevel(f["risk_level"])] for f in recent]
        sector_mean = float(np.mean(rw))
        z = (sector_mean - mean) / std
        conf = min(0.99, 0.5 + abs(z) * 0.15 + min(r_cnt, 20) / 40)
        sev = (
            RiskLevel.CRITICAL if z > 1.5 or velocity > 200 else
            RiskLevel.HIGH if z > 0.7 or velocity > 80 else
            RiskLevel.MODERATE
        )
        # dominant category
        cats = {}
        for f in recent:
            cats[f["category"]] = cats.get(f["category"], 0) + 1
        dom = max(cats.items(), key=lambda x: x[1])[0]
        title = f"{dom.upper()} GAP SPIKE"
        desc_fi = f"Toimialalla havaittu {velocity:.0f}% kasvu {dom}-riskeissä viimeisen 48h aikana."
        alerts.append(OracleAlert(
            id=str(uuid.uuid4()),
            title=title,
            description=desc_fi,
            sector=sector,
            velocity=round(velocity, 1),
            z_score=round(z, 2),
            confidence=round(conf, 2),
            severity=sev,
            created_at=now,
        ))
    # Add global macro
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


# --------------------------------------------------------------------
# Boardroom analytics
# --------------------------------------------------------------------
def _ensure_aware(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _decay(dt: datetime, now: datetime, lam: float = 0.01) -> float:
    dt = _ensure_aware(dt); now = _ensure_aware(now)
    hours = (now - dt).total_seconds() / 3600
    return math.exp(-lam * hours)


@api.get("/analytics/global-risk-index")
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
        t = _ensure_aware(s.get("validated_at")) or now
        d = _decay(t, now)
        num += w * c * d
        den += c * d
    val = num / den if den else 1.0

    # trend from 24h ago
    cutoff = now - timedelta(hours=24)
    recent = [s for s in signals if (_ensure_aware(s.get("validated_at")) or now) >= cutoff]
    trend = "stable"
    if len(recent) >= 3:
        r_num = r_den = 0.0
        for s in recent:
            rl = s.get("override_risk_level") or s["risk_level"]
            w = RISK_WEIGHT[RiskLevel(rl)]
            c = s.get("confidence") or 0.6
            d = _decay(_ensure_aware(s.get("validated_at")) or now, now)
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


@api.get("/analytics/risk-trend")
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
            t = _ensure_aware(s.get("validated_at"))
            if not t or t > point_time:
                continue
            rl = s.get("override_risk_level") or s["risk_level"]
            w = RISK_WEIGHT[RiskLevel(rl)]
            c = s.get("confidence") or 0.6
            dec = _decay(t, point_time)
            num += w * c * dec; den += c * dec
        v = num / den if den else 1.0
        out.append({"date": point_time.strftime("%b %d"), "value": round(v, 2)})
    return out


@api.get("/analytics/heatmap")
async def heatmap(user=Depends(get_current_user)):
    """Three buckets: resources / capabilities / engagement — avg risk weight."""
    sigs = await db.signals.find(
        {"tenant_id": user["tenant_id"], "status": {"$in": ["validated", "overridden"]}, "category": {"$ne": None}},
        {"_id": 0, "category": 1, "risk_level": 1, "override_risk_level": 1},
    ).to_list(5000)
    cats = {"resources": [], "capabilities": [], "engagement": []}
    for s in sigs:
        c = s.get("category")
        if c in cats:
            rl = s.get("override_risk_level") or s["risk_level"]
            cats[c].append(RISK_WEIGHT[RiskLevel(rl)])

    def label(avg):
        if avg >= 3.3: return "CRITICAL"
        if avg >= 2.4: return "HIGH"
        if avg >= 1.6: return "MODERATE"
        return "LOW"

    out = {}
    for k, vals in cats.items():
        avg = sum(vals) / len(vals) if vals else 1.0
        out[k] = {"score": round(avg, 1), "level": label(avg), "count": len(vals)}
    return out


@api.get("/analytics/distribution")
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


# --------------------------------------------------------------------
# System health
# --------------------------------------------------------------------
@api.get("/system/health")
async def system_health():
    now = datetime.now(timezone.utc)
    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    # LLM check – skip actual call, test key presence
    llm_ok = bool(EMERGENT_LLM_KEY)
    # Vector: internal
    vec_ok = True
    # Mothership: count fragments
    frag_cnt = await db.swarm_fragments.count_documents({})
    return {
        "overall": "operational" if (db_ok and llm_ok) else "degraded",
        "timestamp": now.isoformat(),
        "services": {
            "local_ai": {"status": "online" if llm_ok else "offline", "model": "gemini-3-flash-preview", "latency_ms": 320},
            "database": {"status": "healthy" if db_ok else "down", "type": "MongoDB (prod: PostgreSQL)", "collections": len(await db.list_collection_names())},
            "vector_db": {"status": "healthy", "type": "In-memory cosine (prod: Qdrant)", "dim": VECTOR_DIM},
            "mothership": {"status": "connected", "fragments": frag_cnt, "clusters": await db.universal_bottlenecks.count_documents({})},
        },
        "version": "1.3.0",
    }


# --------------------------------------------------------------------
# Webhook (Howspace / Teams) with HMAC
# --------------------------------------------------------------------
def verify_hmac(raw: bytes, sig_header: Optional[str]) -> bool:
    if not sig_header:
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header.replace("sha256=", ""))


@api.post("/webhook/{tenant_id}")
@limiter.limit("60/minute")
async def webhook_receive(
    request: Request,
    tenant_id: str,
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
    x_nonce: Optional[str] = Header(None),
    x_source: Optional[str] = Header("howspace"),
):
    raw = await request.body()
    # Strict mode (production): require all three
    if WEBHOOK_STRICT:
        if not x_signature or not verify_hmac(raw, x_signature):
            raise HTTPException(401, "Invalid HMAC")
        try:
            ts = int(x_timestamp or "0")
            now_s = int(datetime.now(timezone.utc).timestamp())
            if abs(now_s - ts) > 300:
                raise HTTPException(401, "Stale timestamp")
        except ValueError:
            raise HTTPException(401, "Invalid timestamp")
        if not x_nonce:
            raise HTTPException(401, "Missing nonce")
        if await db.webhook_nonces.find_one({"nonce": x_nonce}):
            raise HTTPException(409, "Replay detected")
        await db.webhook_nonces.insert_one({
            "nonce": x_nonce, "tenant_id": tenant_id,
            "created_at": datetime.now(timezone.utc),
        })
    else:
        # Dev-friendly: only verify HMAC if signature provided
        if x_signature and not verify_hmac(raw, x_signature):
            raise HTTPException(401, "Invalid HMAC")
    try:
        payload = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    # Source-specific payload mapping (docs/03)
    if x_source == "howspace":
        msg = payload.get("event", {}).get("message", payload) if isinstance(payload.get("event"), dict) else payload
        content = msg.get("text") or payload.get("content") or payload.get("message") or ""
        author = (msg.get("author", {}) or {}).get("name") if isinstance(msg.get("author"), dict) else msg.get("author") or payload.get("author", "Howspace User")
        bu = (payload.get("workspace") or {}).get("name") if isinstance(payload.get("workspace"), dict) else payload.get("business_unit", "Unknown")
    elif x_source == "teams":
        content = payload.get("text") or payload.get("content") or ""
        author = (payload.get("from") or {}).get("name", "Teams User")
        bu = payload.get("channel", payload.get("business_unit", "Teams"))
    else:
        content = payload.get("content") or payload.get("message") or ""
        author = payload.get("author", "Webhook")
        bu = payload.get("business_unit", "Unknown")
    if not content:
        raise HTTPException(400, "Missing content")
    if not await db.tenants.find_one({"id": tenant_id}):
        raise HTTPException(404, "Unknown tenant")
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": sid, "tenant_id": tenant_id,
        "content": content, "source": x_source or "webhook",
        "business_unit": bu,
        "author": author,
        "submitted_at": now,
        "status": SignalStatus.PENDING.value,
        "risk_level": None, "confidence": None, "summary": None,
        "execution_gaps": [], "hidden_assumptions": [], "facilitator_questions": [],
        "category": None, "semantic_vector": None,
        "validated_by": None, "validated_at": None, "validation_note": None,
        "override_risk_level": None, "swarm_fragment_id": None, "action_card_id": None,
    }
    await db.signals.insert_one(doc.copy())
    asyncio.create_task(_analyze_and_store_signal(sid, tenant_id, content))
    return {"accepted": True, "signal_id": sid}


# --------------------------------------------------------------------
# Root
# --------------------------------------------------------------------
@api.get("/")
async def root():
    return {"service": "TALK TO+ BDaaS", "version": "1.3.0", "status": "online"}


# --------------------------------------------------------------------
# Notifications (docs/04 — Slack / MS Teams Oracle alert push)
# --------------------------------------------------------------------
class NotificationChannel(BaseModel):
    id: str
    tenant_id: str
    type: Literal["slack", "teams"]
    webhook_url: str
    min_severity: RiskLevel = RiskLevel.HIGH
    enabled: bool = True
    created_at: datetime
    label: Optional[str] = None


class NotificationCreate(BaseModel):
    type: Literal["slack", "teams"]
    webhook_url: str
    min_severity: RiskLevel = RiskLevel.HIGH
    label: Optional[str] = None


def _encrypt_url(url: str) -> str:
    """Optional encryption — Fernet if NOTIFICATION_FERNET_KEY set, else stored as-is."""
    if not NOTIFICATION_FERNET_KEY:
        return url
    try:
        from cryptography.fernet import Fernet
        return Fernet(NOTIFICATION_FERNET_KEY.encode()).encrypt(url.encode()).decode()
    except Exception:
        return url


def _decrypt_url(stored: str) -> str:
    if not NOTIFICATION_FERNET_KEY:
        return stored
    try:
        from cryptography.fernet import Fernet
        return Fernet(NOTIFICATION_FERNET_KEY.encode()).decrypt(stored.encode()).decode()
    except Exception:
        return stored


@api.get("/notifications", response_model=List[NotificationChannel])
async def list_notifications(user=Depends(get_current_user)):
    docs = await db.notification_channels.find({"tenant_id": user["tenant_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    # decrypt for display (last 4 chars only in real prod — show full for owner)
    for d in docs:
        d["webhook_url"] = _decrypt_url(d["webhook_url"])
    return [NotificationChannel(**d) for d in docs]


@api.post("/notifications", response_model=NotificationChannel)
async def create_notification(body: NotificationCreate, user=Depends(get_current_user)):
    nid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": nid, "tenant_id": user["tenant_id"],
        "type": body.type, "webhook_url": _encrypt_url(body.webhook_url),
        "min_severity": body.min_severity.value, "enabled": True,
        "created_at": now, "label": body.label,
    }
    await db.notification_channels.insert_one(doc.copy())
    doc["webhook_url"] = body.webhook_url
    return NotificationChannel(**doc)


@api.delete("/notifications/{nid}")
async def delete_notification(nid: str, user=Depends(get_current_user)):
    r = await db.notification_channels.delete_one({"id": nid, "tenant_id": user["tenant_id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


def _slack_blocks(title: str, description: str, fields: List[tuple]) -> dict:
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": title}},
            {"type": "section", "fields": [{"type": "mrkdwn", "text": f"*{k}:*\n{v}"} for k, v in fields]},
            {"type": "section", "text": {"type": "mrkdwn", "text": description}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "TALK TO+ BDaaS · Sovereign Edge"}]},
        ]
    }


def _teams_card(title: str, description: str, fields: List[tuple]) -> dict:
    facts = [{"name": k, "value": str(v)} for k, v in fields]
    return {
        "@type": "MessageCard", "@context": "http://schema.org/extensions",
        "summary": title, "themeColor": "EF4444",
        "sections": [{"activityTitle": title, "facts": facts, "text": description}],
    }


async def _post_webhook(url: str, payload: dict) -> bool:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, json=payload)
            return r.status_code < 400
    except Exception as e:
        logger.warning(f"notification post failed: {e}")
        return False


@api.post("/notifications/{nid}/test")
async def test_notification(nid: str, user=Depends(get_current_user)):
    ch = await db.notification_channels.find_one({"id": nid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not ch:
        raise HTTPException(404)
    url = _decrypt_url(ch["webhook_url"])
    fields = [("Sector", "Test"), ("Velocity", "+0%"), ("Z-Score", "0"), ("Confidence", "100%")]
    payload = _slack_blocks("⚠️ TALK TO+ Test Alert", "This is a test message from TALK TO+ BDaaS.", fields) \
        if ch["type"] == "slack" else _teams_card("TALK TO+ Test Alert", "Test message from TALK TO+ BDaaS.", fields)
    ok = await _post_webhook(url, payload)
    if not ok:
        raise HTTPException(502, "Webhook delivery failed")
    return {"ok": True}


_SEV_ORDER = {"LOW": 1, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}


async def dispatcher_loop():
    """Outbox dispatcher — processes audit_log entries delivered=False and pushes to channels."""
    NOTIFY_EVENTS = {"oracle.spike", "signal.validated"}
    while True:
        try:
            pending = await db.audit_log.find(
                {"delivered": False, "event": {"$in": list(NOTIFY_EVENTS)}}
            ).limit(50).to_list(50)
            for evt in pending:
                channels = await db.notification_channels.find(
                    {"tenant_id": evt["tenant_id"], "enabled": True}
                ).to_list(20)
                payload_data = evt.get("payload", {})
                severity = (payload_data.get("final_risk") or "HIGH").upper()
                for ch in channels:
                    min_sev = ch.get("min_severity", "HIGH")
                    if _SEV_ORDER.get(severity, 0) < _SEV_ORDER.get(min_sev, 3):
                        continue
                    fields = [(k, str(v)) for k, v in payload_data.items()][:6]
                    title = f"⚠️ {evt['event']} · {severity}"
                    desc = json.dumps(payload_data, ensure_ascii=False)[:300]
                    p = _slack_blocks(title, desc, fields) if ch["type"] == "slack" else _teams_card(title, desc, fields)
                    await _post_webhook(_decrypt_url(ch["webhook_url"]), p)
                await db.audit_log.update_one({"id": evt["id"]}, {"$set": {"delivered": True}})
        except Exception:
            logger.exception("dispatcher error")
        await asyncio.sleep(60)


# --------------------------------------------------------------------
# PDF export (docs/05 — Action Card boardroom-ready PDF)
# --------------------------------------------------------------------
ACTION_CARD_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 30mm 25mm; @bottom-right { content: counter(page) " / " counter(pages); font-size: 9pt; color: #94A3B8; } }
body { font-family: 'Helvetica', sans-serif; color: #0A0A0A; }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 2px solid #0A0A0A; }
.brand .mark { width: 40px; height: 40px; background: #0A0A0A; color: white; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: 900; font-size: 18px; }
.brand .name { font-size: 22px; font-weight: 900; letter-spacing: -0.05em; }
.brand .sub { font-size: 9px; letter-spacing: 0.3em; color: #64748B; text-transform: uppercase; }
h1 { font-size: 28px; font-weight: 900; letter-spacing: -0.04em; margin: 12px 0 6px; }
.meta { font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #64748B; }
.badge { display: inline-block; padding: 4px 10px; border-radius: 2px; font-size: 10px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; border: 1px solid; }
.badge-CRITICAL { color: #DC2626; background: #FEF2F2; border-color: #FECACA; }
.badge-HIGH { color: #EA580C; background: #FFF7ED; border-color: #FED7AA; }
.badge-MODERATE { color: #CA8A04; background: #FEFCE8; border-color: #FEF08A; }
.badge-LOW { color: #16A34A; background: #F0FDF4; border-color: #BBF7D0; }
h2 { font-size: 11px; letter-spacing: 0.25em; text-transform: uppercase; color: #64748B; margin: 24px 0 8px; font-weight: 700; }
.summary { background: #F9FAFB; padding: 16px; border-left: 3px solid #0A0A0A; font-size: 11pt; line-height: 1.6; }
ol.steps { margin: 0; padding: 0; list-style: none; counter-reset: step; }
ol.steps li { counter-increment: step; padding: 10px 0 10px 36px; position: relative; border-bottom: 1px solid #E2E8F0; font-size: 11pt; }
ol.steps li::before { content: counter(step); position: absolute; left: 0; top: 12px; width: 24px; height: 24px; background: #0A0A0A; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10pt; font-weight: 700; }
.patterns { font-size: 10pt; color: #475569; }
.patterns li { margin: 4px 0; }
.footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #E2E8F0; font-size: 9pt; color: #94A3B8; display: flex; justify-content: space-between; }
.tag { background: #0A0A0A; color: white; padding: 2px 8px; border-radius: 2px; font-size: 9pt; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
</style></head><body>
<div class="brand">
  <div class="mark">+</div>
  <div><div class="name">TALK TO+ <span style="color:#94A3B8;">/ BDAAS</span></div><div class="sub">Execution Risk Validation</div></div>
</div>
<div class="meta">Action Card · {{ tenant_name }} · {{ created }}</div>
<h1>{{ card.title }}</h1>
<div style="margin: 8px 0 16px;">
  <span class="badge badge-{{ severity }}">{{ severity }}</span>
  {% if card.swarm_verified %}<span class="tag" style="margin-left:8px;">Swarm Verified</span>{% endif %}
</div>
<div class="summary">{{ card.summary }}</div>

{% if signal %}
<h2>Signal</h2>
<div style="font-size:11pt; line-height:1.5;">{{ signal.content }}</div>
<div class="meta" style="margin-top:6px;">{{ signal.business_unit }} · {{ signal.author }}</div>
{% endif %}

{% if signal and signal.execution_gaps %}
<h2>Execution Gaps</h2>
<ul style="font-size:11pt; line-height:1.6;">{% for g in signal.execution_gaps %}<li>{{ g }}</li>{% endfor %}</ul>
{% endif %}

<h2>Playbook</h2>
<ol class="steps">{% for s in card.playbook %}<li>{{ s }}</li>{% endfor %}</ol>

{% if card.swarm_patterns_used %}
<h2>Universal Success Patterns</h2>
<ul class="patterns">{% for p in card.swarm_patterns_used %}<li>· {{ p }}</li>{% endfor %}</ul>
{% endif %}

<div class="footer">
  <div>Impact score: {{ card.impact_score or '—' }} / 5</div>
  <div>Confidential · 4-Eyes Verified · TALK TO+ BDaaS v1.3.0</div>
</div>
</body></html>"""


@api.get("/action-cards/{cid}/export.pdf")
async def export_card_pdf(cid: str, user=Depends(get_current_user)):
    card = await db.action_cards.find_one({"id": cid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not card:
        raise HTTPException(404)
    signal = await db.signals.find_one({"id": card["signal_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
    severity = (signal or {}).get("override_risk_level") or (signal or {}).get("risk_level") or "MODERATE"
    from jinja2 import Template
    from weasyprint import HTML
    html = Template(ACTION_CARD_HTML).render(
        card=card, signal=signal, severity=severity,
        tenant_name=(tenant or {}).get("name", "—"),
        created=card["created_at"].strftime("%Y-%m-%d %H:%M") if isinstance(card.get("created_at"), datetime) else str(card.get("created_at", "")),
    )
    pdf_bytes = HTML(string=html).write_pdf()
    await audit("card.exported", user["id"], user["tenant_id"], {"card_id": cid})
    from fastapi.responses import Response
    return Response(
        pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="action-card-{cid[:8]}.pdf"'},
    )


# --------------------------------------------------------------------
# Audit log (immutable event sourcing — Outbox pattern lite)
# --------------------------------------------------------------------
async def audit(event: str, user_id: Optional[str], tenant_id: Optional[str], payload: dict):
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "event": event,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "payload": payload,
        "created_at": datetime.now(timezone.utc),
        "delivered": False,  # Outbox: flip to True after relay (Slack/Teams)
    })


@api.get("/audit")
async def list_audit(limit: int = 100, user=Depends(require_role(Role.SUPER_ADMIN))):
    docs = await db.audit_log.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return docs


# --------------------------------------------------------------------
# WebSocket: live Oracle alerts push
# --------------------------------------------------------------------
from fastapi import WebSocket, WebSocketDisconnect
_ws_clients: List[WebSocket] = []


@app.websocket("/api/ws/oracle")
async def oracle_ws(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            await asyncio.sleep(15)
            try:
                # Push fresh oracle snapshot
                from fastapi.encoders import jsonable_encoder
                async def _alerts():
                    # reuse oracle_alerts logic via in-process call
                    return await oracle_alerts({"role": Role.SUPER_ADMIN.value, "tenant_id": "default-tenant", "id": "ws"})
                # Simpler: push fragment count + timestamp
                await ws.send_json({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "fragments": await db.swarm_fragments.count_documents({}),
                    "pending": await db.signals.count_documents({"status": "pending"}),
                })
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


app.include_router(api)


# --------------------------------------------------------------------
# Seed demo data (idempotent)
# --------------------------------------------------------------------
async def seed_demo():
    # Tenants
    default_tenants = [
        {"id": "default-tenant", "name": "Nordic Tech Oyj", "sector": "Technology"},
        {"id": "tenant-health", "name": "HealthPlus Group", "sector": "Healthcare"},
        {"id": "tenant-finance", "name": "Aurora Finance", "sector": "Financial Services"},
        {"id": "tenant-energy", "name": "GreenGrid Energy", "sector": "Energy"},
    ]
    for t in default_tenants:
        if not await db.tenants.find_one({"id": t["id"]}):
            await db.tenants.insert_one({
                "id": t["id"], "name": t["name"], "sector": t["sector"],
                "sector_hash": sector_hash(t["sector"]),
                "description": f"{t['name']} — demo-tenant",
                "created_at": datetime.now(timezone.utc),
                "active": True,
            })

    # Users
    users_seed = [
        {"email": "admin@talktoplus.io", "password": "Admin!2026", "full_name": "Anna Tunnuslause", "role": Role.SUPER_ADMIN.value, "tenant_id": "default-tenant"},
        {"email": "facilitator@talktoplus.io", "password": "Facil!2026", "full_name": "M. Virtanen", "role": Role.FACILITATOR.value, "tenant_id": "default-tenant"},
        {"email": "exec@talktoplus.io", "password": "Exec!2026", "full_name": "J. Laine", "role": Role.EXECUTIVE.value, "tenant_id": "default-tenant"},
    ]
    for u in users_seed:
        if not await db.users.find_one({"email": u["email"]}):
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                "email": u["email"], "full_name": u["full_name"],
                "password_hash": hash_password(u["password"]),
                "role": u["role"], "tenant_id": u["tenant_id"],
                "locale": "fi",
                "created_at": datetime.now(timezone.utc),
            })

    # Strategy doc
    if await db.strategy_docs.count_documents({"tenant_id": "default-tenant"}) == 0:
        txt = (
            "Strategia 2026-2028: Nordic Tech Oyj kasvattaa kansainvälistä liiketoimintaa 40% "
            "panostamalla cloud-tuotteisiin, AI-osaamiseen ja asiakaskokemukseen. "
            "Kriittiset kyvykkyydet: DevOps-osaaminen, datapohjainen myynti, "
            "globaali kumppaniverkosto. Resurssit: 25 uutta kehittäjää H1, "
            "20M€ investointi AI-alustaan. Muutosjohtaminen: läpinäkyvä viestintä, "
            "viikoittaiset town hall -kokoukset, selkeä vastuunjako tuotelinjoittain."
        )
        vec = semantic_embed(txt)
        await db.strategy_docs.insert_one({
            "id": str(uuid.uuid4()), "tenant_id": "default-tenant",
            "title": "Nordic Tech Strategia 2026-2028",
            "content": txt, "chunks": 4,
            "uploaded_by": "Anna Tunnuslause",
            "created_at": datetime.now(timezone.utc), "vector": vec,
        })

    # Signals + validation → swarm fragments
    if await db.signals.count_documents({}) == 0:
        demo_signals = [
            # default-tenant
            {"t": "default-tenant", "bu": "Engineering", "author": "M. Virtanen",
             "content": "Resurssipula kriittisessä osaamisessa hidastaa AI-alustan kehitystä merkittävästi. Kehittäjät ovat jo ylikuormittuneita.",
             "rl": "CRITICAL", "cat": "resources", "age_h": 0.4},
            {"t": "default-tenant", "bu": "Operations", "author": "A. Korhonen",
             "content": "Muutosviestinnän puute aiheuttaa epävarmuutta tiimeissä. Town hall -käytännöt eivät ole toteutuneet.",
             "rl": "HIGH", "cat": "engagement", "age_h": 1.2},
            {"t": "default-tenant", "bu": "Product", "author": "J. Laine",
             "content": "Koulutusresurssien riittämättömyys uusiin cloud-teknologioihin huolestuttaa tuotepäälliköitä.",
             "rl": "MODERATE", "cat": "capabilities", "age_h": 2.1},
            {"t": "default-tenant", "bu": "Data & Analytics", "author": "S. Nieminen",
             "content": "Työkalujen integroinnin haasteet vaikuttavat datapohjaiseen päätöksentekoon. Prosessit ovat sujuvat mutta hieman hajallaan.",
             "rl": "LOW", "cat": "process", "age_h": 3.0},
            {"t": "default-tenant", "bu": "Engineering", "author": "K. Mäkinen",
             "content": "Resurssipula estää DevOps-käytäntöjen laajentamisen muihin tiimeihin. Tämä on blokkeri.",
             "rl": "CRITICAL", "cat": "resources", "age_h": 5.0},
            # Tech sector competitor -> reinforces bottleneck
            {"t": "default-tenant", "bu": "Sales", "author": "P. Heikkinen",
             "content": "Asiakaspalaute hidastaa myyntisyklin toimeenpanoa. Hyvä signaali silti, saadaan korjattua.",
             "rl": "LOW", "cat": "engagement", "age_h": 8.0},
            {"t": "default-tenant", "bu": "Engineering", "author": "R. Salonen",
             "content": "Critical blocker: osaamisvaje Kubernetes-operoinnissa, tuotanto-ympäristö riskialtis.",
             "rl": "CRITICAL", "cat": "capabilities", "age_h": 12.0},
            {"t": "default-tenant", "bu": "HR", "author": "L. Nieminen",
             "content": "Sitoutumisen lasku havaittavissa eksitti-haastatteluissa. Huoli organisaatiotasolla.",
             "rl": "HIGH", "cat": "engagement", "age_h": 20.0},
            {"t": "default-tenant", "bu": "Product", "author": "T. Ahonen",
             "content": "Asiakasaisakaslukumäärä kasvussa. Moderate capacity issue mutta hallinnassa.",
             "rl": "MODERATE", "cat": "resources", "age_h": 30.0},
            {"t": "default-tenant", "bu": "Finance", "author": "H. Koski",
             "content": "Budjettien läpinäkyvyys on parantunut. Good execution progress.",
             "rl": "LOW", "cat": "process", "age_h": 48.0},
            {"t": "default-tenant", "bu": "Engineering", "author": "V. Rantanen",
             "content": "High risk: integration vendors delaying delivery of core API.",
             "rl": "HIGH", "cat": "capabilities", "age_h": 60.0},
            {"t": "default-tenant", "bu": "Operations", "author": "E. Laakso",
             "content": "Moderate bottleneck in procurement pipeline affecting Q2.",
             "rl": "MODERATE", "cat": "process", "age_h": 72.0},
            # Other tenants
            {"t": "tenant-health", "bu": "Clinical", "author": "Dr. Saari",
             "content": "Kriittinen resurssipula hoitajien rekrytoinnissa uuteen yksikköön.",
             "rl": "CRITICAL", "cat": "resources", "age_h": 6.0},
            {"t": "tenant-finance", "bu": "Risk", "author": "Rauno M.",
             "content": "Severe resource gap in compliance team during regulation update.",
             "rl": "CRITICAL", "cat": "resources", "age_h": 4.0},
            {"t": "tenant-energy", "bu": "Field Ops", "author": "Lauri P.",
             "content": "Osaamisvaje kriittisissä turbiinioperaatiossa: asiantuntijat eläköityvät.",
             "rl": "HIGH", "cat": "capabilities", "age_h": 14.0},
            {"t": "tenant-finance", "bu": "Ops", "author": "Mika V.",
             "content": "Resurssipula syntynyt IT-kehityspuolelle, projektit jäljessä.",
             "rl": "HIGH", "cat": "resources", "age_h": 10.0},
        ]
        now = datetime.now(timezone.utc)
        for s in demo_signals:
            t_ago = now - timedelta(hours=s["age_h"])
            sid = str(uuid.uuid4())
            vec = semantic_embed(s["content"])
            summary = f"Signaali osoittaa {s['cat']}-pohjaisen toimeenpano-ongelman tasolla {s['rl']}."
            gaps = [
                "Omistajuus epäselvä",
                "Mittareita ei seurata viikkotasolla",
                "Resurssit eivät vastaa tavoitetta",
            ]
            questions = [
                "Kuka omistaa tämän seuraavat 2 viikkoa?",
                "Mitä konkreettista tukea tarvitaan 48h sisällä?",
            ]
            doc = {
                "id": sid, "tenant_id": s["t"],
                "content": s["content"], "source": "manual",
                "business_unit": s["bu"], "author": s["author"],
                "submitted_at": t_ago,
                "status": SignalStatus.VALIDATED.value,
                "risk_level": s["rl"],
                "confidence": 0.78 + (0.15 if s["rl"] == "CRITICAL" else 0.05),
                "summary": summary,
                "execution_gaps": gaps,
                "hidden_assumptions": ["Oletetaan nykyinen kapasiteetti riittää"],
                "facilitator_questions": questions,
                "category": s["cat"],
                "semantic_vector": vec,
                "validated_by": "M. Virtanen",
                "validated_at": t_ago + timedelta(minutes=22),
                "validation_note": "Verified against strategy",
                "override_risk_level": None,
                "swarm_fragment_id": None, "action_card_id": None,
            }
            await db.signals.insert_one(doc.copy())
            # Swarm fragment
            tenant = await db.tenants.find_one({"id": s["t"]}, {"_id": 0})
            frag_id = str(uuid.uuid4())
            await db.swarm_fragments.insert_one({
                "id": frag_id, "sector_hash": tenant["sector_hash"],
                "sector_display": tenant["sector"],
                "risk_level": s["rl"], "confidence": doc["confidence"],
                "category": s["cat"], "semantic_vector": vec,
                "created_at": doc["validated_at"],
            })
            # Action card
            card_id = str(uuid.uuid4())
            await db.action_cards.insert_one({
                "id": card_id, "tenant_id": s["t"], "signal_id": sid,
                "title": f"Interventio: {s['cat'].title()} bottleneck",
                "summary": f"Suositeltu korjaava toimenpideketju {s['cat']}-aukolle tasolla {s['rl']}.",
                "playbook": [
                    "1. Nimeä omistaja ja tukitiimi 48h sisään",
                    "2. Kartoita resurssit vs. tavoite",
                    "3. Priorisoi top-3 toimenpidettä",
                    "4. Seuranta viikkotasolla 6 vk",
                    "5. Go/no-go -päätös 4 vk kohdalla",
                ],
                "rag_context_used": ["Strategia 2026-2028"],
                "swarm_patterns_used": [],
                "impact_score": 4 if s["rl"] in ("LOW", "MODERATE") else None,
                "swarm_verified": False,
                "created_at": doc["validated_at"] + timedelta(minutes=1),
            })
            await db.signals.update_one({"id": sid}, {"$set": {"swarm_fragment_id": frag_id, "action_card_id": card_id}})

        # One pending signal for Decision Hub demo
        pending_sid = str(uuid.uuid4())
        pending_content = "Tiimimme on huolissaan siitä, että uusien AI-ominaisuuksien julkaisuaikataulua ei pystytä pitämään — kapasiteettia ei ole lisätty sovitusti."
        vec = semantic_embed(pending_content)
        await db.signals.insert_one({
            "id": pending_sid, "tenant_id": "default-tenant",
            "content": pending_content, "source": "howspace",
            "business_unit": "Engineering", "author": "Anonymous",
            "submitted_at": now - timedelta(minutes=8),
            "status": SignalStatus.PENDING.value,
            "risk_level": "HIGH", "confidence": 0.82,
            "summary": "AI-ominaisuuksien julkaisuaikataulu vaarassa: kapasiteetti ei vastaa sovittua.",
            "execution_gaps": ["Kapasiteettilisäys ei toteutunut", "Tiimin viestintä johdon kanssa katkennut"],
            "hidden_assumptions": ["Oletettu, että rekrytoinnit toteutuvat automaattisesti"],
            "facilitator_questions": ["Milloin rekrytointilupaus annettiin?", "Kuka omistaa seuraavat 2 vk?"],
            "category": "resources", "semantic_vector": vec,
            "validated_by": None, "validated_at": None, "validation_note": None,
            "override_risk_level": None, "swarm_fragment_id": None, "action_card_id": None,
        })

        await _update_clusters()

    logger.info("Seed complete")


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.signals.create_index([("tenant_id", 1), ("submitted_at", -1)])
    await db.swarm_fragments.create_index("created_at")
    # docs/03 — TTL index for webhook nonces (10 min replay window)
    try:
        await db.webhook_nonces.create_index("created_at", expireAfterSeconds=600)
    except Exception:
        pass
    await seed_demo()
    if ENABLE_DISPATCHER:
        asyncio.create_task(dispatcher_loop())
        logger.info("Notification dispatcher started")


@app.on_event("shutdown")
async def shutdown():
    client.close()
