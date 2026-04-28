# TALK TO+ BDaaS — Product Requirements Document

**Version:** 1.3.0 · **Status:** Production-ready MVP · **Date:** Apr 2026

## 1. Original problem statement
Build TALK TO+ BDaaS — Execution Risk Validation Engine. Privacy-first, "Sovereign Edge + Mothership" hybrid AI platform that turns unstructured organizational signals into actionable strategic intelligence. Bilingual FI/EN. 8 views matching reference dashboard screenshot.

## 2. Architecture (MVP → Prod)
| Layer | MVP (this build) | Production target |
|------|------------------|-------------------|
| Frontend | React 18 + Tailwind + Recharts + Phosphor icons | unchanged |
| Backend | FastAPI + Motor (async MongoDB) | FastAPI |
| Database | MongoDB (single tenant collection logical isolation) | PostgreSQL with Row-Level Security |
| Vector | In-memory cosine + hashed pseudo-embeddings (256-dim) | Qdrant + BAAI/bge-m3 |
| LLM | Gemini 3 Flash via emergentintegrations | Local vLLM + Gemma 4B |
| Auth | Custom JWT (HS256, 24h) + bcrypt | unchanged |
| Webhook | HMAC-SHA256 (Howspace/Teams) | unchanged |

## 3. Implemented (Apr 2026)
- **Auth**: register/login/me, 3 demo users seeded (super_admin, facilitator, executive)
- **Boardroom View**: Executive Heatmap (3 cards), Global Risk Index trend (exponential decay λ=0.01), Risk Distribution donut, Oracle Alerts (Z-score + Risk Velocity), Universal Bottlenecks, Recent Validated Signals, System Status — all live data
- **Signals Radar**: list/filter/create signal, auto AI-analysis on create (Gemini 3 Flash + heuristic fallback)
- **Decision Hub**: 4-Eyes principle UI — validate / override / dismiss with note + override risk level, auto-creates SwarmFragment + ActionCard
- **Global Intelligence**: Universal Bottleneck clusters (greedy cosine ≥ 0.55), fragments count, sectors affected, super_admin recompute
- **Action Cards**: Hybrid RAG playbooks (auto-generated using strategy RAG context + cross-tenant success patterns from Mothership when impact_score≥4), 1-5 star impact rating
- **Strategy RAG**: doc CRUD with semantic embedding for retrieval
- **Tenants**: multi-tenant CRUD (sector_hash anonymized for swarm)
- **System Health**: Local AI / Database / Vector DB / Mothership status, polled every 15s
- **Oracle**: Z-score anomaly detection per sector, Risk Velocity tracking (48h vs prev-48h), severity classification
- **Webhook**: `/api/webhook/{tenant_id}` with HMAC validation (dev-friendly when no signature)
- **Bilingual UI**: full FI/EN toggle in sidebar header + auth page
- **Seed data**: 4 tenants, 3 users, 16 signals (15 validated + 1 pending), 15 swarm fragments, 15 action cards, 4 universal bottlenecks, 1 strategy doc

## 4. Test status
- **Backend**: 20/20 pytest pass, all 21 critical endpoints verified
- **Frontend**: Login + Boardroom + Decision Hub validate flow verified visually (GRI updated 2.6→2.84, new PROCESS GAP SPIKE oracle alert appeared after validation, signals count 12→14)

## 4b. Erä 1 additions (Apr 2026)
- ✅ **Audit log** — every signal validation logged to `audit_log` collection (Outbox pattern: `delivered=false`)
- ✅ **`GET /api/audit`** endpoint (super_admin only)
- ✅ **WebSocket `/api/ws/oracle`** — pushes fragment count + pending count every 15s
- ✅ **`/app/HANDOFF.md`** + **`/app/docs/01-07*.md`** — autonomous agent handoff package

## 4c. Erä 2 additions (Apr 2026)
- ✅ **PDF export** (docs/05): `GET /api/action-cards/{id}/export.pdf` — boardroom-ready WeasyPrint PDF + Frontend "PDF" button
- ✅ **Notifications** (docs/04): `Notifications` collection + CRUD `/api/notifications` + `/test` endpoint + Slack/Teams payload formatters + Outbox dispatcher loop (gated by `ENABLE_DISPATCHER` env) + Frontend `/notifications` page with channel management
- ✅ **Webhook strict mode** (docs/03): `WEBHOOK_STRICT=true` enforces HMAC + nonce + timestamp window; TTL-indexed `webhook_nonces` collection (10-min replay window); Howspace + Teams payload mapping
- ✅ **Security hardening** (docs/07): security headers middleware (X-Frame-Options, CSP, HSTS, Referrer-Policy), `slowapi` rate limiting wired (10/min login, 5/min register, 60/min webhook), `CORS_ORIGINS` env allowlist, encryption helper for stored webhook URLs
- ✅ **vLLM abstraction** (docs/06): `_llm_chat_json()` unified interface; toggles between Gemini 3 Flash and local vLLM via `USE_LOCAL_LLM=true` + `VLLM_BASE_URL`
- ✅ **Postgres scaffold** (docs/01): `postgres_adapter.py` stub + feature flag `USE_POSTGRES` + Tenant RLS context manager template
- ⏭ **Server.py split** (docs/02): refactor plan written to `_split_plan.py` (deferred — pure mechanical, high regression risk in single session)

## 4d. Erä 3 additions (Apr 28, 2026)
- ✅ **Backend modular refactor** (docs/02): server.py 1905 LOC → 78 LOC. New layout:
  - `core.py` — config, Mongo, JWT/auth helpers, audit, rate limiter
  - `models.py` — all Pydantic models + enums
  - `services/` — `embedding`, `ai`, `swarm`, `signal_pipeline`, `notifications`, `pdf`
  - `routers/` — `auth`, `tenants`, `signals`, `action_cards`, `strategy_docs`, `swarm`, `oracle`, `analytics`, `system`, `webhook`, `notifications`, `ws`
  - `seed.py` — demo data (Metso/Nordea/Wärtsilä)
- ✅ **Visual fixes (Boardroom)**:
  - Heatmap: 3-column grid → **4-column** including the previously hidden `process` bucket
  - Empty buckets render as "—" with neutral styling instead of misleading "LOW"
  - Risk Distribution donut: percentage-based radii (62%/92%) + smaller center text (text-2xl) so the total never overlaps the ring
- ✅ **Tests**: 21/21 backend regression pass after refactor

## 5. Demo credentials
- Super Admin: `admin@talktoplus.io` / `Admin!2026`
- Facilitator: `facilitator@talktoplus.io` / `Facil!2026`
- Executive: `exec@talktoplus.io` / `Exec!2026`

## 6. Backlog (P1/P2)
- **P1**: Migrate to PostgreSQL + Qdrant; replace pseudo-embedding with BGE-M3
- ✅ ~~P1: Split server.py into routers/services modules~~ (done Apr 28, 2026)
- **P2**: Real Howspace/Teams webhook integration with replay-attack nonce store
- **P2**: WebSocket push for live Oracle alerts
- **P2**: Action Card export to PDF/Slack
- **P2**: Audit log + immutable event sourcing (Outbox pattern)
- **P2**: Local vLLM deployment for full data sovereignty

## 7. Known minor items
- Dev-mode React overlay may flash during rapid navigation right after a slow Gemini call (non-blocking, production silent)
- `_update_clusters` rebuilds collection — consider per-category upsert for high concurrency
