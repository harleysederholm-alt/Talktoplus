# Current Project State — Snapshot

**Last updated**: end of MVP build session

## Build status
- Backend: ✅ Running, 100% pytest pass (20/20)
- Frontend: ✅ Running, all 8 views functional
- Demo data: ✅ Seeded (4 tenants, 3 users, 16 signals, 15 fragments, 15 action cards, 4 bottlenecks)

## Live demo flow (verified working)
1. Login → `admin@talktoplus.io` / `Admin!2026`
2. Boardroom shows live data (GRI, heatmap, oracle alerts, bottlenecks)
3. Decision Hub → 1 pending signal awaits validation
4. Click "Validate" → action card auto-generated, GRI updates, new oracle spike alert appears
5. Action Cards page → impact score 1-5 stars
6. Strategy RAG → CRUD docs (1 seeded)
7. Tenants → 4 listed, super_admin can add
8. System Health → 4 services all green
9. Language toggle FI ↔ EN works

## What's implemented (DO NOT redo)
- Auth (JWT + bcrypt + 3 demo users)
- 8 views (Boardroom, Signals Radar, Decision Hub, Global Intelligence, Action Cards, Strategy RAG, Tenants, System Health)
- 21 API endpoints under `/api/*` (all in `server.py`)
- AI: Gemini 3 Flash via emergentintegrations + heuristic fallback
- Z-score Oracle + Risk Velocity tracking
- Exponential decay Global Risk Index (λ=0.01)
- Greedy cosine clustering for Universal Bottlenecks (threshold 0.55)
- Hybrid RAG (cross-tenant Universal Success Patterns when impact_score≥4)
- HMAC webhook (Howspace/Teams ready)
- Audit log + Outbox pattern (`audit_log` collection)
- WebSocket `/api/ws/oracle`
- Bilingual FI/EN

## What's NOT done — pick from these in order
See `/app/docs/01_postgres_qdrant_migration.md` → `07_production_checklist.md`

## Files modified to know
- `/app/backend/server.py` (1400 LOC — split planned in docs/02)
- `/app/backend/.env` (do NOT change MONGO_URL, DB_NAME)
- `/app/frontend/src/App.js` (routes)
- `/app/frontend/src/components/Layout.jsx` (sidebar)
- `/app/frontend/src/pages/*.jsx` (8 views)
- `/app/frontend/src/i18n.js` (bilingual)
- `/app/frontend/.env` (REACT_APP_BACKEND_URL — do NOT change)
