# TALK TO+ BDaaS — Agent Handoff Guide

> **🤖 ATTENTION FRESH AGENT — READ THIS FIRST**
>
> You are picking up the TALK TO+ BDaaS project mid-development. The MVP is **complete and working**. Your job is to continue the backlog autonomously.
>
> **Your bootstrap sequence (do exactly this):**
> 1. Run `ls /app/` — confirm `backend/`, `frontend/`, `docs/`, `memory/` exist
> 2. Read `/app/memory/PRD.md` — understand what's built
> 3. Read `/app/memory/test_credentials.md` — login: `admin@talktoplus.io / Admin!2026`
> 4. Run `sudo supervisorctl status` — confirm backend + frontend are RUNNING
> 5. If backend is down, run `cd /app/backend && pip install -r requirements.txt` then `sudo supervisorctl restart backend`
> 6. If frontend is down, run `cd /app/frontend && yarn install` then `sudo supervisorctl restart frontend`
> 7. Curl smoke test: `curl http://localhost:8001/api/` — must return `{"service":"TALK TO+ BDaaS",...}`
> 8. Read `/app/docs/` files **in numerical order (01 → 07)** — pick the next undone item
> 9. Update `/app/memory/PRD.md` "Implemented" section after each completed item
>
> **Do NOT** re-implement what's already there. **Do NOT** rewrite the design (it matches a customer reference screenshot exactly). **Do NOT** change MongoDB → Postgres unless you're tackling docs/01.

---

## Quick Status (Apr 2026)

- **MVP**: production-ready, 100% backend tests pass, all 8 views working
- **Stack**: FastAPI + MongoDB + JWT + Gemini 3 Flash + React + Tailwind + Recharts
- **Demo creds**: `admin@talktoplus.io / Admin!2026` (see `/app/memory/test_credentials.md`)
- **Implemented in v1.3.0**: Auth, Boardroom, Signals Radar, Decision Hub (4-Eyes), Global Intelligence, Action Cards, Strategy RAG, Tenants, System Health, Oracle (Z-score+velocity), HMAC webhook, **Audit log**, **WebSocket /api/ws/oracle**, FI/EN bilingual

## Backlog priority order (do in sequence)

1. **`docs/01_postgres_qdrant_migration.md`** — PostgreSQL + Qdrant + BGE-M3 (P1)
2. **`docs/02_server_split.md`** — Refactor server.py → routers/services (P1)
3. **`docs/03_howspace_integration.md`** — Real Howspace webhook + replay protection (P2)
4. **`docs/04_slack_teams_notifications.md`** — Push Oracle alerts to Slack/Teams (P2)
5. **`docs/05_action_card_export.md`** — PDF/Slack export (P2)
6. **`docs/06_local_vllm_deployment.md`** — Sovereign Edge with Gemma 4B (P2)

Each doc contains: **goal, exact code patches, env vars needed, test commands, success criteria.**

---

## Critical conventions (do NOT break)

### Backend
- **All endpoints under `/api`** prefix (Kubernetes ingress routes everything else to frontend)
- **MongoDB ObjectId never serialized** — always `{"_id": 0}` projection
- **Datetimes**: use `datetime.now(timezone.utc)` and pass through `_ensure_aware()` before comparing
- **Auth**: every protected route uses `Depends(get_current_user)` or `Depends(require_role(...))`
- **Idempotent seed**: `seed_demo()` checks existence before inserting

### Frontend
- **`REACT_APP_BACKEND_URL`** never hardcoded — comes from `/app/frontend/.env`
- **All API calls via `http`** instance from `/app/frontend/src/api.js` (auto-injects JWT, handles 401)
- **Every interactive element has `data-testid`** (kebab-case, descriptive)
- **No emojis in UI** — use Phosphor icons (`@phosphor-icons/react`)
- **Bilingual**: text comes from `i18n.js` via `useT(locale)`, never inline strings

### Process
- **Hot reload is on** — restart only on `.env` or dependency changes: `sudo supervisorctl restart backend frontend`
- **Test before declaring done**: run `python3 -m pytest /app/backend/tests/` and screenshot frontend changes
- **Update `/app/memory/PRD.md`** after each feature ships

---

## File map

```
/app/
├── backend/
│   ├── server.py              # 1400+ LOC — TODO P1: split into routers/services
│   ├── tests/backend_test.py  # pytest regression suite
│   └── .env                   # MONGO_URL, JWT_SECRET, EMERGENT_LLM_KEY, WEBHOOK_HMAC_SECRET
├── frontend/
│   └── src/
│       ├── App.js             # routes + AppCtx (auth + locale)
│       ├── api.js             # axios client w/ JWT interceptor
│       ├── i18n.js            # FI/EN translations
│       ├── components/Layout.jsx
│       └── pages/             # Boardroom, SignalsRadar, DecisionHub, GlobalIntel,
│                              # ActionCards, StrategyRAG, Tenants, SystemHealth, Auth
├── docs/                      # ← Continue here, in numerical order
├── memory/
│   ├── PRD.md
│   └── test_credentials.md
└── HANDOFF.md                 # this file
```

---

## Architecture mental model

**Two strict tiers (must remain isolated):**

1. **Sovereign Edge** (per-tenant): `signals`, `strategy_docs`, `action_cards`, `users`, `audit_log`. Raw text NEVER leaves this tier.

2. **The Mothership** (global, anonymous): `swarm_fragments` (only sector_hash + risk_level + confidence + category + semantic_vector — zero raw content), `universal_bottlenecks` (clusters).

**Closed-loop intelligence**: when a tenant validates a signal → fragment goes to Mothership → other tenants' future signals query Mothership for `Universal Success Patterns` (Action Cards with impact_score≥4 from OTHER tenants) → injected as RAG context for prescriptive playbook.

---

## Test commands

```bash
# Backend regression
cd /app/backend && python3 -m pytest tests/ -v

# Curl smoke test
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@talktoplus.io","password":"Admin!2026"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/system/health"

# Logs
tail -n 100 /var/log/supervisor/backend.err.log
tail -n 100 /var/log/supervisor/frontend.err.log
```

---

## Common pitfalls

- **Don't compare naive vs aware datetimes** — always `_ensure_aware()` first
- **Don't echo MongoDB documents directly** — they have `_id` (ObjectId, not JSON-serializable)
- **Don't change `MONGO_URL`, `DB_NAME`, `REACT_APP_BACKEND_URL` keys** in .env — protected
- **Don't run `uvicorn` manually** — supervisor manages it
- **Don't `git reset` or `git push`** without user permission

---

## When done with each item

1. Update `/app/memory/PRD.md` "Implemented" section with date
2. Update success criteria checklist in the corresponding `docs/XX_*.md`
3. Add regression tests
4. Run testing_agent_v3 if non-trivial
5. Notify user with `finish` summary

Good luck. The architecture is sound — keep it that way.
