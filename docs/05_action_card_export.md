# 05 · Action Card Export (PDF / Slack / Teams) (P2)

**Goal**: Export Action Cards as boardroom-ready PDF, or push directly to Slack/Teams as a structured message. Boardroom-ready presentation is a key sales talking point.

## Estimated effort
~1.5h.

## Backend deps
```
weasyprint==63.1   # HTML→PDF with proper Finnish character support
jinja2==3.1.4
```

## Endpoint
```python
@api.get("/action-cards/{cid}/export.pdf")
async def export_card_pdf(cid: str, user=Depends(get_current_user)):
    card = await db.action_cards.find_one({"id": cid, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not card:
        raise HTTPException(404)
    signal = await db.signals.find_one({"id": card["signal_id"]}, {"_id": 0})
    html = render_template("action_card.html", card=card, signal=signal, tenant_name="...")
    pdf = HTML(string=html).write_pdf()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="action-card-{cid[:8]}.pdf"'})
```

## Template (`backend/templates/action_card.html`)
- Brand header with TALK TO+ logo (SVG)
- Risk badge (color matching severity)
- Signal summary
- Execution gaps as bullets
- Numbered playbook with bold step numbers
- Universal Success Patterns (if any)
- Footer with timestamp + facilitator name + impact score
- Use IBM Plex Sans web fonts embedded as base64

## Frontend
Add "Export PDF" button to `ActionCards.jsx`:
```jsx
<a
  data-testid={`export-${c.id}`}
  href={`${API}/action-cards/${c.id}/export.pdf`}
  target="_blank"
  className="..."
>Export PDF</a>
```

## Slack/Teams direct push
Add `POST /api/action-cards/{cid}/push?channel_id=X` that uses notification dispatcher to format the card as Block Kit / Adaptive Card and post to a stored channel.

## Success criteria
- [ ] PDF renders Finnish characters correctly (ä, ö, å)
- [ ] Risk badge color matches severity
- [ ] Multi-page if playbook >5 steps
- [ ] Slack push delivers a clickable button "View in Boardroom"
- [ ] Auditable: every export logged to `audit_log` with event `card.exported`
