# 03 · Howspace + Teams Webhook Integration (P2)

**Goal**: Real-world webhook ingestion from [Howspace](https://howspace.com/) and Microsoft Teams. Replay protection via nonce store.

## Howspace specifics
Howspace doesn't publish a public webhook API. Two paths:
- **Path A — Native event**: Customer enables "Outgoing webhooks" in their Howspace workspace settings (enterprise-only) and points it to `https://talktoplus.io/api/webhook/{tenant_id}`.
- **Path B — Polling fallback**: Use Howspace REST API to poll dialogues every 5 min. (Implement only if Path A blocked.)

## Estimated effort
~1.5h for Path A + replay protection.

## Backend additions

### 1. Nonce store (Mongo collection with TTL index)
```python
# in seed/startup
await db.webhook_nonces.create_index("created_at", expireAfterSeconds=600)  # 10-min window
```

### 2. Update webhook handler in `server.py`
```python
@api.post("/webhook/{tenant_id}")
async def webhook_receive(
    tenant_id: str,
    req: Request,
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
    x_nonce: Optional[str] = Header(None),
    x_source: Optional[str] = Header("howspace"),
):
    raw = await req.body()
    # 1. HMAC required in prod
    if not x_signature or not verify_hmac(raw, x_signature):
        raise HTTPException(401, "Invalid HMAC")
    # 2. Timestamp window (5 min)
    try:
        ts = int(x_timestamp or "0")
        now_s = int(datetime.now(timezone.utc).timestamp())
        if abs(now_s - ts) > 300:
            raise HTTPException(401, "Stale timestamp")
    except ValueError:
        raise HTTPException(401, "Invalid timestamp")
    # 3. Nonce check (no replay)
    if not x_nonce:
        raise HTTPException(401, "Missing nonce")
    existing = await db.webhook_nonces.find_one({"nonce": x_nonce})
    if existing:
        raise HTTPException(409, "Replay detected")
    await db.webhook_nonces.insert_one({
        "nonce": x_nonce, "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc),
    })
    # ... existing payload processing ...
```

### 3. Howspace payload shape
Map Howspace dialogue events to Signal:
```python
def map_howspace_payload(payload: dict) -> dict:
    # Howspace sends nested events
    msg = payload.get("event", {}).get("message", {})
    return {
        "content": msg.get("text", ""),
        "business_unit": payload.get("workspace", {}).get("name", "Unknown"),
        "author": msg.get("author", {}).get("name", "Anonymous"),
        "source": "howspace",
    }
```

### 4. Teams adapter
Teams sends Adaptive Card responses. Add `x_source=teams` branch:
```python
if x_source == "teams":
    # Teams payload: {"type": "message", "text": "...", "from": {"name": "..."}}
    content = payload.get("text", "")
    author = payload.get("from", {}).get("name", "Teams User")
```

### 5. Outgoing ack
Howspace expects 200 OK within 3s. Already async — fine.

## Customer setup docs (`/app/docs/CUSTOMER_HOWSPACE_SETUP.md`)
Generate signing secret per tenant: `WEBHOOK_HMAC_SECRET_<tenant_id>` env. Customer copies signing secret + URL into Howspace admin → Outgoing webhooks.

## Success criteria
- [ ] HMAC + nonce + timestamp all enforced (no `--unsafe` mode)
- [ ] Replay rejected with 409
- [ ] Stale timestamp rejected with 401
- [ ] Howspace test payload creates Signal in correct tenant
- [ ] Teams test payload creates Signal with `source=teams`
- [ ] TTL index removes old nonces automatically
