"""
TALK TO+ BDaaS — Pydantic models and enums.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, EmailStr


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
    PENDING = "pending"
    VALIDATED = "validated"
    OVERRIDDEN = "overridden"
    DISMISSED = "dismissed"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"


class BottleneckCategory(str, Enum):
    RESOURCES = "resources"
    CAPABILITIES = "capabilities"
    ENGAGEMENT = "engagement"
    PROCESS = "process"


# --------------------------------------------------------------------
# User / Auth
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


class RoleSwitchReq(BaseModel):
    role: Role


class ProfileUpdateReq(BaseModel):
    full_name: Optional[str] = None
    locale: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None


# --------------------------------------------------------------------
# Tenants
# --------------------------------------------------------------------
class Tenant(BaseModel):
    id: str
    name: str
    sector: str
    sector_hash: str
    created_at: datetime
    active: bool = True
    description: Optional[str] = None


class TenantCreate(BaseModel):
    name: str
    sector: str
    description: Optional[str] = None


# --------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------
class Signal(BaseModel):
    id: str
    tenant_id: str
    content: str
    source: str = "manual"
    business_unit: str
    author: str
    submitted_at: datetime
    status: SignalStatus
    risk_level: Optional[RiskLevel] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    execution_gaps: List[str] = []
    hidden_assumptions: List[str] = []
    facilitator_questions: List[str] = []
    category: Optional[BottleneckCategory] = None
    semantic_vector: Optional[List[float]] = None
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    validation_note: Optional[str] = None
    override_risk_level: Optional[RiskLevel] = None
    swarm_fragment_id: Optional[str] = None
    action_card_id: Optional[str] = None


class SignalCreate(BaseModel):
    content: str
    business_unit: str
    author: Optional[str] = None
    source: str = "manual"


class ValidationReq(BaseModel):
    decision: Literal["validate", "override", "dismiss", "escalate", "in_progress"]
    note: Optional[str] = None
    override_risk_level: Optional[RiskLevel] = None


# --------------------------------------------------------------------
# Action Cards
# --------------------------------------------------------------------
class ActionCard(BaseModel):
    id: str
    tenant_id: str
    signal_id: str
    title: str
    summary: str
    playbook: List[str]
    rag_context_used: List[str] = []
    swarm_patterns_used: List[str] = []
    impact_score: Optional[int] = None
    swarm_verified: bool = False
    swarm_verified_count: int = 0
    status: Literal["pending_validation", "validated", "in_progress", "dismissed", "escalated"] = "pending_validation"
    facilitator: Optional[str] = None
    created_at: datetime


# --------------------------------------------------------------------
# Strategy RAG
# --------------------------------------------------------------------
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


# --------------------------------------------------------------------
# Swarm
# --------------------------------------------------------------------
class SwarmFragment(BaseModel):
    id: str
    sector_hash: str
    risk_level: RiskLevel
    confidence: float
    category: BottleneckCategory
    semantic_vector: List[float]
    created_at: datetime


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
    velocity: float
    z_score: float
    confidence: float
    severity: RiskLevel
    created_at: datetime


# --------------------------------------------------------------------
# Notifications
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
