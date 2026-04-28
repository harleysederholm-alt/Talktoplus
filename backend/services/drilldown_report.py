"""
TALK TO+ BDaaS — Drill-down deep-dive PDF for a single bottleneck category.
Renders explainer + cross-sector data + tenant-specific signals + recommended playbook.
"""
EOH = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 22mm 18mm 24mm 18mm;
  @bottom-left { content: "{{ tenant_name }} · Confidential · Drill-down: {{ category_label }}"; font-size: 8pt; color: #94A3B8; }
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
.box { border-left: 3px solid #0A0A0A; background: #F9FAFB; padding: 12px 14px; margin: 12px 0; font-size: 10pt; line-height: 1.55; color: #1F2937; }
ol.steps { margin: 0; padding: 0; list-style: none; counter-reset: step; }
ol.steps li { counter-increment: step; padding: 8px 0 8px 32px; position: relative; border-bottom: 1px solid #F1F5F9; font-size: 10pt; line-height: 1.5; }
ol.steps li::before { content: counter(step); position: absolute; left: 0; top: 8px; width: 22px; height: 22px; background: #0A0A0A; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9pt; font-weight: 700; }
table { width: 100%; border-collapse: collapse; font-size: 9pt; }
th { text-align: left; font-size: 8px; letter-spacing: 0.25em; text-transform: uppercase; color: #64748B; padding: 6px 4px; border-bottom: 1px solid #E2E8F0; font-weight: 700; }
td { padding: 8px 4px; border-bottom: 1px solid #F1F5F9; vertical-align: top; }
.badge { display: inline-block; padding: 2px 6px; font-size: 8px; font-weight: 800; letter-spacing: 0.2em; text-transform: uppercase; border: 1px solid; }
.badge-CRITICAL { color: #DC2626; background: #FEF2F2; border-color: #FECACA; }
.badge-HIGH { color: #EA580C; background: #FFF7ED; border-color: #FED7AA; }
.badge-MODERATE { color: #CA8A04; background: #FEFCE8; border-color: #FEF08A; }
.badge-LOW { color: #16A34A; background: #F0FDF4; border-color: #BBF7D0; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.tag { font-size: 8pt; letter-spacing: 0.15em; text-transform: uppercase; padding: 3px 8px; background: white; border: 1px solid #E2E8F0; font-weight: 700; }
.footnote { margin-top: 18px; font-size: 8pt; color: #94A3B8; line-height: 1.5; border-top: 1px solid #E2E8F0; padding-top: 8px; }
</style></head><body>

<div class="brand">
  <div class="mark">+</div>
  <div><div class="name">TALK TO+ <span style="color:#94A3B8;">/ BDAAS</span></div><div class="sub">Drill-down · {{ category_label }}</div></div>
</div>

<div class="kicker">{{ tenant_name }} · {{ generated_at }}</div>
<h1>{{ category_label }} — Deep Dive</h1>
<div class="lede">{{ explainer }}</div>

<div class="kpis">
  <div class="kpi"><div class="l">Signals (tenant)</div><div class="v">{{ tenant_count }}</div><div class="s">avg risk weight {{ tenant_avg_weight }}</div></div>
  <div class="kpi"><div class="l">Swarm fragments</div><div class="v">{{ swarm_count }}</div><div class="s">{{ swarm_pct }}% of all fragments</div></div>
  <div class="kpi"><div class="l">Cross-sector</div><div class="v">{{ sectors_count }}</div><div class="s">sectors affected</div></div>
  <div class="kpi"><div class="l">Severity</div><div class="v">{{ tenant_level }}</div><div class="s">tenant-level rating</div></div>
</div>

<h2>Why this matters</h2>
<div class="box">{{ why_it_matters }}</div>

<h2>Tenant signals · {{ tenant_count }}</h2>
{% if tenant_signals %}
<table>
  <thead><tr><th style="width:50%;">Signal</th><th>Business unit</th><th>Risk</th><th>Validated</th></tr></thead>
  <tbody>
  {% for s in tenant_signals %}
    <tr>
      <td>{{ s.content }}</td>
      <td style="color:#475569;">{{ s.business_unit }}</td>
      <td><span class="badge badge-{{ s.risk }}">{{ s.risk }}</span></td>
      <td style="font-family: monospace; font-size: 8.5pt; color:#64748B;">{{ s.when }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<div class="lede" style="color:#64748B;">No tenant signals in this category yet — the bottleneck is detected via cross-sector swarm intelligence only.</div>
{% endif %}

<h2>Cross-sector swarm view</h2>
<div class="lede" style="margin-bottom:8px;">Anonymized fragments from peer organizations (Sovereign Edge — zero raw content):</div>
<table>
  <thead><tr><th>Sector</th><th>Fragments</th><th>Avg severity</th><th>Last 48h velocity</th></tr></thead>
  <tbody>
  {% for r in cross_sector %}
    <tr>
      <td><strong>{{ r.sector }}</strong></td>
      <td style="font-family: monospace;">{{ r.count }}</td>
      <td><span class="badge badge-{{ r.severity }}">{{ r.severity }}</span></td>
      <td style="font-family: monospace; color:{{ '#DC2626' if r.velocity > 30 else '#0A0A0A' }};">+{{ r.velocity }}%</td>
    </tr>
  {% endfor %}
  </tbody>
</table>

<h2>Recommended playbook (swarm-validated)</h2>
<ol class="steps">
  {% for step in playbook %}<li>{{ step }}</li>{% endfor %}
</ol>

<h2>Sectors where detected</h2>
<div class="tags">
  {% for s in related_sectors %}<span class="tag">{{ s }}</span>{% endfor %}
</div>

<div class="footnote">
  Drill-down generated by TALK TO+ BDaaS · Closed-loop swarm intelligence. Cross-sector data is BAAI/bge-m3 cosine-clustered (≥0.55) over hashed sector identifiers — no raw content leaves the tenant boundary.
</div>

</body></html>"""


def render_drilldown_pdf(payload: dict) -> bytes:
    from jinja2 import Template
    from weasyprint import HTML
    return HTML(string=Template(EOH).render(**payload)).write_pdf()
