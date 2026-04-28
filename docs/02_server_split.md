# 02 · Split server.py into routers + services (P1)

**Goal**: Refactor 1400-LOC `server.py` into modular routers and services. Improves maintainability, enables parallel agent work.

## Estimated effort
30-45 min. Pure mechanical refactor — no behavior change.

## Target structure

```
backend/
├── server.py                  # ~50 lines: app init, includes routers
├── core/
│   ├── config.py              # env var loading
│   ├── db.py                  # Mongo client + db
│   ├── auth.py                # JWT, password, get_current_user, require_role
│   └── deps.py                # Common dependencies
├── models/
│   ├── enums.py               # RiskLevel, Role, SignalStatus, BottleneckCategory
│   ├── user.py                # UserPublic, LoginReq, RegisterReq, TokenResp
│   ├── tenant.py
│   ├── signal.py              # Signal, SignalCreate, ValidationReq
│   ├── action_card.py
│   ├── strategy_doc.py
│   └── swarm.py               # SwarmFragment, UniversalBottleneck, OracleAlert
├── services/
│   ├── ai.py                  # analyze_signal_ai, generate_action_card_ai
│   ├── embedding.py           # semantic_embed, cosine, sector_hash
│   ├── swarm_math.py          # _update_clusters, _query_universal_patterns
│   ├── analytics.py           # _decay, GRI, trend, heatmap, distribution
│   └── oracle.py              # alerts, z-score
├── routers/
│   ├── auth.py                # /api/auth/*
│   ├── tenants.py             # /api/tenants/*
│   ├── signals.py             # /api/signals/*
│   ├── action_cards.py
│   ├── strategy_docs.py
│   ├── swarm.py               # /api/swarm/*
│   ├── oracle.py              # /api/oracle/*
│   ├── analytics.py           # /api/analytics/*
│   ├── system.py              # /api/system/health, /api/audit
│   ├── webhook.py             # /api/webhook/*
│   └── ws.py                  # /api/ws/*
├── seed.py                    # seed_demo()
└── tests/backend_test.py
```

## How

1. Create files above with empty stubs
2. Move chunks in this order (keep `server.py` working between each step):
   - First: `core/config.py`, `core/db.py`, `models/*`
   - Then: `services/*` (AI, embedding, math)
   - Then: `routers/*` one at a time
   - Last: `seed.py`
3. In `server.py`:
```python
from fastapi import FastAPI
from core.config import settings
from routers import auth, tenants, signals, action_cards, strategy_docs, swarm, oracle, analytics, system, webhook, ws
app = FastAPI(title="TALK TO+ BDaaS", version="1.3.0")
# CORS...
for r in [auth, tenants, signals, action_cards, strategy_docs, swarm, oracle, analytics, system, webhook]:
    app.include_router(r.router, prefix="/api")
ws.register(app)
@app.on_event("startup")
async def _start():
    from seed import seed_demo
    await seed_demo()
```
4. Run `pytest` after each move to catch regressions.

## Success criteria
- [ ] All 21 endpoints respond identically
- [ ] No file > 200 LOC
- [ ] Pytest passes 100%
- [ ] Frontend untouched, still works
