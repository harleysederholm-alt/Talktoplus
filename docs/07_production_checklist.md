# 07 · Final Production Deployment Checklist

**Goal**: Final pre-launch checklist when all P1/P2 items above are complete.

## Security
- [ ] Rotate `JWT_SECRET` (current contains `change-me` marker)
- [ ] Rotate `WEBHOOK_HMAC_SECRET` per tenant
- [ ] Enable TLS at ingress (Let's Encrypt or commercial cert)
- [ ] Set CORS_ORIGINS to explicit allowed domains (currently `*`)
- [ ] Enable rate limiting (slowapi) on `/api/auth/login`, `/api/webhook/*`
- [ ] Add security headers: CSP, HSTS, X-Frame-Options
- [ ] Encrypt notification webhook URLs at rest (Fernet)
- [ ] Implement `delete_account` flow (GDPR)
- [ ] Enable audit log retention policy (e.g. 7 years for SOC2)

## Performance
- [ ] Add Redis cache for `/api/analytics/*` endpoints (60s TTL)
- [ ] Add database connection pooling (asyncpg pool size = 10*workers)
- [ ] Add CDN for frontend static assets
- [ ] Run k6 load test: target 1000 RPS on read endpoints, 100 RPS on writes

## Observability
- [ ] Sentry for error tracking (frontend + backend)
- [ ] OpenTelemetry traces (Honeycomb / Datadog)
- [ ] Prometheus metrics: `/metrics` endpoint via prometheus_fastapi_instrumentator
- [ ] Grafana dashboards: GRI per tenant, alert push success rate, AI latency p50/p95/p99

## CI/CD
- [ ] GitHub Actions: pytest on PR, build Docker images, push to registry
- [ ] Staging environment with isolated Postgres + Qdrant
- [ ] Blue/green deploys

## Compliance
- [ ] SOC2 Type II audit prep
- [ ] GDPR DPA + Privacy Notice
- [ ] DPIA for swarm fragments (legal review)
- [ ] Penetration test by 3rd party

## Customer onboarding
- [ ] Self-serve tenant provisioning (currently super_admin only)
- [ ] Stripe billing integration (use stripe playbook)
- [ ] Howspace setup wizard with copy-paste secrets
- [ ] In-app tour (Shepherd.js)

## Marketing site
- [ ] Public landing page (separate Next.js project)
- [ ] Whitepaper PDF download gating with email
- [ ] Demo video (Boardroom walkthrough, 90s)
