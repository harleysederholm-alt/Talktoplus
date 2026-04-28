# TALK TO+ BDaaS — Test Credentials

## Demo Users (all tenants: `default-tenant`)
| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@talktoplus.io | Admin!2026 |
| Facilitator | facilitator@talktoplus.io | Facil!2026 |
| Executive | exec@talktoplus.io | Exec!2026 |

All users seeded idempotently on backend startup. Auth uses JWT (24h expiry) via `/api/auth/login`.
