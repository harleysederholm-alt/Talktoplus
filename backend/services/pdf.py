"""
TALK TO+ BDaaS — Action Card PDF rendering (WeasyPrint).
"""
from datetime import datetime

ACTION_CARD_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 30mm 25mm; @bottom-right { content: counter(page) " / " counter(pages); font-size: 9pt; color: #94A3B8; } }
body { font-family: 'Helvetica', sans-serif; color: #0A0A0A; }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 2px solid #0A0A0A; }
.brand .mark { width: 40px; height: 40px; background: #0A0A0A; color: white; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: 900; font-size: 18px; }
.brand .name { font-size: 22px; font-weight: 900; letter-spacing: -0.05em; }
.brand .sub { font-size: 9px; letter-spacing: 0.3em; color: #64748B; text-transform: uppercase; }
h1 { font-size: 28px; font-weight: 900; letter-spacing: -0.04em; margin: 12px 0 6px; }
.meta { font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #64748B; }
.badge { display: inline-block; padding: 4px 10px; border-radius: 2px; font-size: 10px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; border: 1px solid; }
.badge-CRITICAL { color: #DC2626; background: #FEF2F2; border-color: #FECACA; }
.badge-HIGH { color: #EA580C; background: #FFF7ED; border-color: #FED7AA; }
.badge-MODERATE { color: #CA8A04; background: #FEFCE8; border-color: #FEF08A; }
.badge-LOW { color: #16A34A; background: #F0FDF4; border-color: #BBF7D0; }
h2 { font-size: 11px; letter-spacing: 0.25em; text-transform: uppercase; color: #64748B; margin: 24px 0 8px; font-weight: 700; }
.summary { background: #F9FAFB; padding: 16px; border-left: 3px solid #0A0A0A; font-size: 11pt; line-height: 1.6; }
ol.steps { margin: 0; padding: 0; list-style: none; counter-reset: step; }
ol.steps li { counter-increment: step; padding: 10px 0 10px 36px; position: relative; border-bottom: 1px solid #E2E8F0; font-size: 11pt; }
ol.steps li::before { content: counter(step); position: absolute; left: 0; top: 12px; width: 24px; height: 24px; background: #0A0A0A; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10pt; font-weight: 700; }
.patterns { font-size: 10pt; color: #475569; }
.patterns li { margin: 4px 0; }
.footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #E2E8F0; font-size: 9pt; color: #94A3B8; display: flex; justify-content: space-between; }
.tag { background: #0A0A0A; color: white; padding: 2px 8px; border-radius: 2px; font-size: 9pt; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
</style></head><body>
<div class="brand">
  <div class="mark">+</div>
  <div><div class="name">TALK TO+ <span style="color:#94A3B8;">/ BDAAS</span></div><div class="sub">Execution Risk Validation</div></div>
</div>
<div class="meta">Action Card · {{ tenant_name }} · {{ created }}</div>
<h1>{{ card.title }}</h1>
<div style="margin: 8px 0 16px;">
  <span class="badge badge-{{ severity }}">{{ severity }}</span>
  {% if card.swarm_verified %}<span class="tag" style="margin-left:8px;">Swarm Verified</span>{% endif %}
</div>
<div class="summary">{{ card.summary }}</div>

{% if signal %}
<h2>Signal</h2>
<div style="font-size:11pt; line-height:1.5;">{{ signal.content }}</div>
<div class="meta" style="margin-top:6px;">{{ signal.business_unit }} · {{ signal.author }}</div>
{% endif %}

{% if signal and signal.execution_gaps %}
<h2>Execution Gaps</h2>
<ul style="font-size:11pt; line-height:1.6;">{% for g in signal.execution_gaps %}<li>{{ g }}</li>{% endfor %}</ul>
{% endif %}

<h2>Playbook</h2>
<ol class="steps">{% for s in card.playbook %}<li>{{ s }}</li>{% endfor %}</ol>

{% if card.swarm_patterns_used %}
<h2>Universal Success Patterns</h2>
<ul class="patterns">{% for p in card.swarm_patterns_used %}<li>· {{ p }}</li>{% endfor %}</ul>
{% endif %}

<div class="footer">
  <div>Impact score: {{ card.impact_score or '—' }} / 5</div>
  <div>Confidential · 4-Eyes Verified · TALK TO+ BDaaS v1.3.0</div>
</div>
</body></html>"""


def render_action_card_pdf(card: dict, signal: dict, tenant_name: str, severity: str) -> bytes:
    from jinja2 import Template
    from weasyprint import HTML
    created = card["created_at"].strftime("%Y-%m-%d %H:%M") if isinstance(card.get("created_at"), datetime) else str(card.get("created_at", ""))
    html = Template(ACTION_CARD_HTML).render(
        card=card, signal=signal, severity=severity,
        tenant_name=tenant_name, created=created,
    )
    return HTML(string=html).write_pdf()
