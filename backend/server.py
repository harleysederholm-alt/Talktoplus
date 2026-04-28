"""
TALK TO+ BDaaS — Execution Risk Validation Engine
FastAPI app entrypoint. Wires routers, middlewares, lifespan.
"""
import asyncio

from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core import db, logger, limiter, ENABLE_DISPATCHER, ENABLE_EMAIL_SCHEDULER, CORS_ALLOW_LIST
from routers import (
    auth, tenants, signals, action_cards, strategy_docs,
    swarm, oracle, analytics, system, webhook, notifications, reports, ws,
)

app = FastAPI(title="TALK TO+ BDaaS", version="1.3.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Security headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if request.url.scheme == "https":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_LIST, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Mount all /api routers
api = APIRouter(prefix="/api")
for r in (
    auth.router, tenants.router, signals.router, action_cards.router,
    strategy_docs.router, swarm.router, oracle.router, analytics.router,
    system.router, webhook.router, notifications.router, reports.router,
):
    api.include_router(r)
app.include_router(api)

# WebSocket
ws.register(app)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.signals.create_index([("tenant_id", 1), ("submitted_at", -1)])
    await db.swarm_fragments.create_index("created_at")
    try:
        await db.webhook_nonces.create_index("created_at", expireAfterSeconds=600)
    except Exception:
        pass
    from seed import seed_demo
    await seed_demo()
    if ENABLE_DISPATCHER:
        from services.notifications import dispatcher_loop
        asyncio.create_task(dispatcher_loop())
        logger.info("Notification dispatcher started")
    if ENABLE_EMAIL_SCHEDULER:
        from services.email import monthly_scheduler_loop, is_configured
        if is_configured():
            asyncio.create_task(monthly_scheduler_loop())
            logger.info("Monthly email scheduler started")
        else:
            logger.warning("ENABLE_EMAIL_SCHEDULER=true but RESEND_API_KEY missing — scheduler disabled")


@app.on_event("shutdown")
async def shutdown():
    from core import client
    client.close()
