# 04 · Slack / MS Teams Oracle Notifications (P2)

**Goal**: Push high-severity Oracle alerts (Z-score > 1.5 OR velocity > 200%) to Slack/Teams in real time. Critical for executive early warning system — biggest single revenue lever.

## Estimated effort
~1.5h. User must provide Slack webhook URL and/or Teams webhook URL.

## Required from user
- **Slack**: Incoming Webhook URL — go to https://api.slack.com/apps → Create App → Incoming Webhooks → Add to channel → copy URL
- **Teams**: Channel webhook URL — channel → connectors → "Incoming Webhook" → configure → copy URL

Store per-tenant in `notification_channels` collection.

## Schema
```python
class NotificationChannel(BaseModel):
    id: str
    tenant_id: str
    type: Literal["slack", "teams"]
    webhook_url: str  # encrypted at rest in prod
    min_severity: RiskLevel  # only push >= this level
    enabled: bool = True
    created_at: datetime
```

## Endpoints (add to `routers/notifications.py`)
- `GET /api/notifications` — list channels
- `POST /api/notifications` — add channel
- `DELETE /api/notifications/{id}`
- `POST /api/notifications/{id}/test` — send test alert

## Background dispatcher (`services/dispatcher.py`)
Run every 60s as `asyncio.create_task` from startup:
```python
async def dispatcher_loop():
    while True:
        try:
            # find audit_log entries delivered=False AND event in NOTIFY_EVENTS
            pending = await db.audit_log.find(
                {"delivered": False, "event": {"$in": ["oracle.spike", "signal.validated"]}}
            ).to_list(50)
            for evt in pending:
                channels = await db.notification_channels.find(
                    {"tenant_id": evt["tenant_id"], "enabled": True}
                ).to_list(20)
                for ch in channels:
                    await send_notification(ch, evt)
                await db.audit_log.update_one({"id": evt["id"]}, {"$set": {"delivered": True}})
        except Exception:
            logger.exception("dispatcher error")
        await asyncio.sleep(60)
```

## Slack format (Block Kit)
```python
async def send_slack(url: str, alert: dict):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"⚠️ {alert['title']}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Sector:*\n{alert['sector']}"},
            {"type": "mrkdwn", "text": f"*Velocity:*\n+{alert['velocity']}%"},
            {"type": "mrkdwn", "text": f"*Z-Score:*\n{alert['z_score']}"},
            {"type": "mrkdwn", "text": f"*Confidence:*\n{int(alert['confidence']*100)}%"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": alert["description"]}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Open Boardroom"},
             "url": f"https://app.talktoplus.io/?alert={alert['id']}"}
        ]},
    ]
    async with httpx.AsyncClient() as c:
        await c.post(url, json={"blocks": blocks}, timeout=10)
```

## Teams Adaptive Card
Similar — use Adaptive Card schema. Template available at https://adaptivecards.io.

## Trigger Oracle.spike events
In `oracle_alerts` endpoint or via cron, when an alert is freshly computed and severity >= HIGH, write to `audit_log` with event `oracle.spike` so dispatcher picks it up. Use deduplication: skip if same `(sector, dom_category)` was emitted in last 6h.

## Success criteria
- [ ] User can add Slack channel via UI in `/notifications` page (build new view)
- [ ] Test button sends a sample alert and returns 200
- [ ] Real CRITICAL alert reaches Slack within 60s of validation
- [ ] No duplicate alerts within 6h window
- [ ] `delivered=true` flagged in audit_log after success
