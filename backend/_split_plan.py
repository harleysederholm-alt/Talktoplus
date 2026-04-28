"""
docs/02 — Server split scaffolding (READ-ONLY notes module).

This file documents the intended target structure. Refactor was deferred to
keep MVP green and avoid breaking the working build. To execute the split:

1. Create the directory tree below.
2. Move sections of /app/backend/server.py one at a time.
3. Run pytest after each move (from /app/backend/tests/).
4. Replace server.py with the thin entry point at the bottom.

Target tree
-----------
backend/
├── server.py              (~50 LOC entry point — see template below)
├── core/
│   ├── config.py          (env vars + feature flags)
│   ├── db.py              (Mongo client + indexes)
│   ├── auth.py            (JWT, password ctx, get_current_user, require_role)
│   └── deps.py            (shared deps, e.g. limiter)
├── models/
│   ├── enums.py
│   ├── user.py
│   ├── tenant.py
│   ├── signal.py
│   ├── action_card.py
│   ├── strategy_doc.py
│   ├── swarm.py
│   └── notification.py
├── services/
│   ├── ai.py              (analyze_signal_ai, generate_action_card_ai, _llm_chat_json)
│   ├── embedding.py       (semantic_embed, cosine, sector_hash, _ensure_aware)
│   ├── swarm_math.py      (_update_clusters, _query_universal_patterns)
│   ├── analytics.py       (_decay, GRI, trend, heatmap, distribution)
│   ├── oracle.py          (oracle_alerts logic)
│   ├── pdf.py             (export_card_pdf template + render)
│   ├── notifications.py   (_post_webhook, _slack_blocks, _teams_card, dispatcher_loop)
│   └── audit.py           (audit, list_audit)
├── routers/
│   ├── auth.py
│   ├── tenants.py
│   ├── signals.py
│   ├── action_cards.py
│   ├── strategy_docs.py
│   ├── swarm.py
│   ├── oracle.py
│   ├── analytics.py
│   ├── system.py
│   ├── webhook.py
│   ├── notifications.py
│   └── ws.py
└── seed.py


Template — final server.py
--------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from core.config import settings
from core.deps import limiter
from core.db import db, client
from routers import (auth, tenants, signals, action_cards, strategy_docs,
                     swarm, oracle, analytics, system, webhook, notifications, ws)
from seed import seed_demo
import asyncio

app = FastAPI(title="TALK TO+ BDaaS", version="1.3.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ALLOW_LIST,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for r in [auth, tenants, signals, action_cards, strategy_docs, swarm, oracle,
          analytics, system, webhook, notifications]:
    app.include_router(r.router, prefix="/api")
ws.register(app)

@app.on_event("startup")
async def _start():
    await db.users.create_index("email", unique=True)
    await db.signals.create_index([("tenant_id", 1), ("submitted_at", -1)])
    await db.swarm_fragments.create_index("created_at")
    await db.webhook_nonces.create_index("created_at", expireAfterSeconds=600)
    await seed_demo()
    if settings.ENABLE_DISPATCHER:
        from services.notifications import dispatcher_loop
        asyncio.create_task(dispatcher_loop())

@app.on_event("shutdown")
async def _stop():
    client.close()
"""
