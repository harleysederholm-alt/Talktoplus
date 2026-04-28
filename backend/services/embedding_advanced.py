"""
TALK TO+ BDaaS — Advanced semantic embedding (BGE-M3) abstraction.

This module wraps a real production embedding (sentence-transformers / BGE-M3)
behind the same `semantic_embed(text)` signature used by services/embedding.py.

Activation: set `USE_BGE_M3=true` in /app/backend/.env (model is downloaded on first call).
Fallback: when disabled OR sentence-transformers is missing, callers should keep using
the deterministic hash-pseudo-embedding from services/embedding.py.

This file is an opt-in production swap — it is NOT imported by default.
"""
import os
import logging
from typing import List

logger = logging.getLogger("talktoplus.embedding_advanced")

USE_BGE_M3 = os.environ.get("USE_BGE_M3", "false").lower() == "true"
_MODEL = None  # cached singleton


def _load_model():
    """Lazy-load the sentence-transformers model. Returns None if unavailable."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not USE_BGE_M3:
        return None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning("sentence-transformers not installed — `pip install sentence-transformers` to enable BGE-M3")
        return None
    try:
        # Multilingual, 1024-dim, FI/EN both strong
        _MODEL = SentenceTransformer("BAAI/bge-m3")
        logger.info("BGE-M3 model loaded (1024-dim multilingual)")
        return _MODEL
    except Exception as e:
        logger.exception(f"BGE-M3 load failed: {e}")
        return None


def is_available() -> bool:
    return USE_BGE_M3 and _load_model() is not None


def semantic_embed(text: str) -> List[float]:
    """Returns a 1024-dim BGE-M3 embedding (or empty list when unavailable).
    The caller is expected to fall back to services/embedding.semantic_embed when this returns []."""
    m = _load_model()
    if m is None:
        return []
    vec = m.encode(text or "", normalize_embeddings=True)
    return vec.tolist() if hasattr(vec, "tolist") else list(vec)
