"""
TALK TO+ BDaaS — Deterministic semantic embedding & helpers.
Stable hash-projection embedding (production replacement: BGE-M3 → Qdrant).
"""
import math
import hashlib
from datetime import datetime, timezone
from typing import List

import numpy as np

VECTOR_DIM = 256


def semantic_embed(text: str) -> List[float]:
    """Stable pseudo-embedding for clustering. Hash n-grams into buckets.
    When `USE_BGE_M3=true` and sentence-transformers is installed, this transparently
    swaps to a real BGE-M3 (1024-dim multilingual) embedding."""
    try:
        from services.embedding_advanced import semantic_embed as _bge_embed, is_available
        if is_available():
            v = _bge_embed(text)
            if v:
                return v
    except Exception:
        pass

    vec = np.zeros(VECTOR_DIM, dtype=np.float32)
    words = [w.lower() for w in text.split() if len(w) > 2]
    if not words:
        return vec.tolist()
    for w in words:
        h = int(hashlib.sha256(w.encode()).hexdigest(), 16) % VECTOR_DIM
        vec[h] += 1.0
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


def ensure_aware(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def decay(dt: datetime, now: datetime, lam: float = 0.01) -> float:
    dt = ensure_aware(dt); now = ensure_aware(now)
    hours = (now - dt).total_seconds() / 3600
    return math.exp(-lam * hours)
