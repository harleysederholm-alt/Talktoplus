"""
TALK TO+ BDaaS — Executive Summary PDF (C-level quarterly board report).
Aggregates GRI, trend, top oracle alerts, top signals, heatmap, distribution.
"""
from datetime import datetime

EXECUTIVE_REPORT_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 22mm 18mm 24mm 18mm;
  @bottom-left { content: "{{ tenant_name }} · Confidential"; font-size: 8pt; color: #94A3B8; }
  @bottom-right { content: counter(page) " / " counter(pages); font-size: 8pt; color: #94A3B8; } }
body { font-family: 'Helvetica', sans-serif; color: #0A0A0A; }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; padding-bottom: 10px; border-bottom: 2px solid #0A0A0A; }
.brand .mark { width: 36px; height: 36px; background: #0A0A0A; color: white; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: 900; font-size: 16px; }
.brand .name { font-size: 19px; font-weight: 900; letter-spacing: -0.04em; }
.brand .sub { font-size: 8px; letter-spacing: 0.3em; color: #64748B; text-transform: uppercase; }
.kicker { font-size: 9px; letter-spacing: 0.3em; text-transform: uppercase; color: #64748B; }
h1 { font-size: 26px; font-weight: 900; letter-spacing: -0.04em; margin: 6px 0 4px; }
h2 { font-size: 10px; letter-spacing: 0.3em; text-transform: uppercase; color: #64748B; margin: 22px 0 8px; font-weight: 700; padding-bottom: 4px; border-bottom: 1px solid #E2E8F0; }
.lede { font-size: 10.5pt; line-height: 1.55; color: #1F2937; }
.kpis { display: flex; gap: 8px; margin: 14px 0 0; }
.kpi { flex: 1; border: 1px solid #E2E8F0; padding: 10px 12px; }
.kpi .l { font-size: 8px; letter-spacing: 0.25em; text-transform: uppercase; color: #64748B; font-weight: 700; }
.kpi .v { font-size: 22px; font-weight: 900; letter-spacing: -0.03em; margin-top: 4px; }
.kpi .s { font-size: 9px; color: #64748B; margin-top: 2px; }
.trend { display: flex; align-items: flex-end; height: 56px; gap: 3px; margin-top: 8px; }
.trend .b { flex: 1; background: #0A0A0A; }
.cats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.cat { border: 1px solid #E2E8F0; padding: 10px; }
.cat .l { font-size: 8px; letter-spacing: 0.25em; text-transform: uppercase; color: #64748B; font-weight: 700; }
.cat .v { font-size: 16px; font-weight: 900; margin-top: 4px; letter-spacing: -0.02em; }
.bar { height: 4px; background: #F1F5F9; margin-top: 6px; }
.bar > span { display: block; height: 100%; }
.alert { padding: 10px 12px; border-left: 3px solid #0A0A0A; background: #F9FAFB; margin: 0 0 8px; }
.alert .t { font-size: 11pt; font-weight: 800; letter-spacing: -0.01em; }
.alert .meta { font-size: 8px; letter-spacing: 0.25em; text-transform: uppercase; color: #64748B; margin-top: 4px; }
.alert .desc { font-size: 9.5pt; color: #334155; margin-top: 4px; line-height: 1.5; }
table.signals { width: 100%; border-collapse: collapse; font-size: 9pt; }
table.signals th { text-align: left; font-size: 8px; letter-spacing: 0.25em; text-transform: uppercase; color: #64748B; padding: 6px 4px; border-bottom: 1px solid #E2E8F0; font-weight: 700; }
table.signals td { padding: 8px 4px; border-bottom: 1px solid #F1F5F9; vertical-align: top; }
.badge { display: inline-block; padding: 2px 6px; font-size: 8px; font-weight: 800; letter-spacing: 0.2em; text-transform: uppercase; border: 1px solid; }
.badge-CRITICAL, .sev-CRITICAL { color: #DC2626; background: #FEF2F2; border-color: #FECACA; }
.badge-HIGH, .sev-HIGH { color: #EA580C; background: #FFF7ED; border-color: #FED7AA; }
.badge-MODERATE, .sev-MODERATE { color: #CA8A04; background: #FEFCE8; border-color: #FEF08A; }
.badge-LOW, .sev-LOW { color: #16A34A; background: #F0FDF4; border-color: #BBF7D0; }
.badge-NONE { color: #64748B; background: #F8FAFC; border-color: #E2E8F0; }
.dist-row { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 9pt; }
.dist-row .swatch { width: 10px; height: 10px; border-radius: 2px; }
.footnote { margin-top: 14px; font-size: 8pt; color: #94A3B8; line-height: 1.5; border-top: 1px solid #E2E8F0; padding-top: 8px; }
</style></head><body>

<div class="brand">
  <div class="mark">+</div>
  <div><div class="name">TALK TO+ <span style="color:#94A3B8;">/ BDAAS</span></div><div class="sub">Execution Risk Validation · Quarterly Board Report</div></div>
</div>

<div class="kicker">{{ tenant_name }} · {{ generated_at }} · {{ window_label }}</div>
<h1>{{ headline }}</h1>
<div class="lede">{{ lede }}</div>

<div class="kpis">
  <div class="kpi"><div class="l">Global Risk Index</div><div class="v">{{ gri.value }}</div><div class="s">Trend: {{ gri.trend }}</div></div>
  <div class="kpi"><div class="l">Active HIGH+</div><div class="v">{{ gri.active }}</div><div class="s">of {{ gri.total }} validated</div></div>
  <div class="kpi"><div class="l">Swarm fragments</div><div class="v">{{ swarm_count }}</div><div class="s">Zero-knowledge anonymized</div></div>
  <div class="kpi"><div class="l">Action Cards</div><div class="v">{{ card_count }}</div><div class="s">{{ swarm_verified_count }} swarm-verified</div></div>
</div>

<h2>Risk Index — {{ window_label }}</h2>
<div class="trend">
  {% for p in trend %}
    <div class="b" title="{{ p.date }}: {{ p.value }}" style="height: {{ (p.value / 4 * 100) | round(0) }}%; opacity: {{ 0.4 + (loop.index / trend|length) * 0.6 }};"></div>
  {% endfor %}
</div>
<div class="kicker" style="margin-top: 4px;">{{ trend[0].date }} → {{ trend[-1].date }} · scale 0–4 (LOW → CRITICAL)</div>

<h2>Sovereignty Heatmap</h2>
<div class="cats">
  {% for c in heatmap %}
  <div class="cat">
    <div class="l">{{ c.label }}</div>
    <div class="v">{% if c.count > 0 %}{{ c.level }}{% else %}—{% endif %}</div>
    <div class="bar"><span class="sev-{{ c.level }}" style="width: {{ (c.score / 4 * 100) | round(0) }}%;"></span></div>
    <div class="s" style="font-size:8px;color:#64748B;margin-top:4px;">{{ c.count }} signals · score {{ c.score }}</div>
  </div>
  {% endfor %}
</div>

<h2>Top Oracle Alerts</h2>
{% if alerts %}
  {% for a in alerts %}
  <div class="alert">
    <div class="t">{{ a.title }} <span class="badge badge-{{ a.severity }}" style="margin-left:6px;">{{ a.severity }}</span></div>
    <div class="meta">{{ a.sector }} · velocity +{{ a.velocity }}% · z-score {{ a.z_score }} · confidence {{ (a.confidence * 100) | round(0) }}%</div>
    <div class="desc">{{ a.description }}</div>
  </div>
  {% endfor %}
{% else %}
  <div class="lede" style="color:#64748B;">No anomalies detected in the current window.</div>
{% endif %}

<h2>Recently Validated Signals</h2>
<table class="signals">
  <thead><tr><th style="width:55%;">Signal</th><th>Business unit</th><th>Risk</th><th>Validated</th></tr></thead>
  <tbody>
  {% for s in signals %}
    <tr>
      <td>{{ s.content_short }}</td>
      <td style="color:#475569;">{{ s.business_unit }}</td>
      <td><span class="badge badge-{{ s.risk }}">{{ s.risk }}</span></td>
      <td style="font-family: monospace; font-size: 8.5pt; color:#64748B;">{{ s.when }}</td>
    </tr>
  {% endfor %}
  {% if signals|length == 0 %}
    <tr><td colspan="4" style="color:#94A3B8;font-style:italic;">No validated signals in window.</td></tr>
  {% endif %}
  </tbody>
</table>

<h2>Risk Distribution</h2>
{% for d in distribution %}
  <div class="dist-row">
    <span class="swatch" style="background: {{ d.color }};"></span>
    <span style="flex:1; font-weight:600;">{{ d.name }}</span>
    <span style="font-family: monospace; color:#64748B;">{{ d.value }} signals · {{ d.percentage }}%</span>
  </div>
{% endfor %}

<div class="footnote">
  Generated by TALK TO+ BDaaS · Closed-loop swarm intelligence · Sovereign Edge data never leaves tenant boundary.<br/>
  Methodology: Risk Index R = Σ(W·C·e<sup>-λt</sup>) / Σ(C·e<sup>-λt</sup>) · λ=0.01/h · severity weights {LOW=1, MODERATE=2, HIGH=3, CRITICAL=4}.
</div>

</body></html>"""


def render_executive_pdf(payload: dict) -> bytes:
    from jinja2 import Template
    from weasyprint import HTML
    html = Template(EXECUTIVE_REPORT_HTML).render(**payload)
    return HTML(string=html).write_pdf()
