"""
TALK TO+ BDaaS — Executive Summary PDF (C-level quarterly board report).
Aggregates GRI, trend, top oracle alerts, top signals, heatmap, distribution.
"""
from datetime import datetime
EXECUTIVE_REPORT_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@page {
  size: A4;
  margin: 25mm 20mm 25mm 20mm;
  @bottom-left {
    content: "{{ tenant_name }} · Confidential · Board Report";
    font-family: 'Helvetica', sans-serif;
    font-size: 7pt;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  @bottom-right {
    content: "Page " counter(page) " of " counter(pages);
    font-family: 'Helvetica', sans-serif;
    font-size: 7pt;
    color: #94A3B8;
  }
}

body {
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  color: #0F172A;
  line-height: 1.5;
  margin: 0;
  padding: 0;
}

/* Header & Branding */
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 40px;
  border-bottom: 1px solid #E2E8F0;
  padding-bottom: 20px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-logo {
  width: 32px;
  height: 32px;
  background: #0F172A;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-weight: 900;
  font-size: 18px;
}
.brand-text {
  font-size: 14px;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-transform: uppercase;
}
.report-meta {
  text-align: right;
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: #64748B;
}

/* Typography */
h1 {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.05em;
  margin: 0 0 12px 0;
  color: #0F172A;
  line-height: 1.1;
}
.lede {
  font-size: 11pt;
  color: #475569;
  max-width: 90%;
  margin-bottom: 30px;
}
h2 {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.25em;
  color: #64748B;
  margin: 40px 0 16px 0;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
h2::after {
  content: "";
  flex: 1;
  height: 1px;
  background: #F1F5F9;
}

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 30px;
}
.kpi-card {
  background: #F8FAFC;
  border: 1px solid #F1F5F9;
  padding: 16px;
  border-radius: 8px;
}
.kpi-label {
  font-size: 7px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: #64748B;
  font-weight: 700;
  margin-bottom: 8px;
}
.kpi-value {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #0F172A;
}
.kpi-sub {
  font-size: 8px;
  color: #94A3B8;
  margin-top: 4px;
}

/* Charts & Visuals */
.trend-container {
  background: #0F172A;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.trend-bars {
  display: flex;
  align-items: flex-end;
  height: 60px;
  gap: 4px;
}
.trend-bar {
  flex: 1;
  background: #38BDF8;
  border-radius: 2px 2px 0 0;
}
.trend-axis {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 7px;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.heatmap-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.heat-card {
  border: 1px solid #E2E8F0;
  padding: 14px;
  border-radius: 6px;
}
.heat-label {
  font-size: 7px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: #64748B;
  margin-bottom: 6px;
}
.heat-value {
  font-size: 14px;
  font-weight: 800;
  margin-bottom: 8px;
}
.progress-bg {
  height: 4px;
  background: #F1F5F9;
  border-radius: 2px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
}

/* Alerts */
.alert-item {
  padding: 16px;
  background: white;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  margin-bottom: 12px;
  page-break-inside: avoid;
}
.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.alert-title {
  font-size: 12px;
  font-weight: 800;
  color: #0F172A;
}
.alert-meta {
  font-size: 7px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: #64748B;
}
.alert-desc {
  font-size: 10px;
  color: #475569;
  line-height: 1.5;
}

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}
th {
  text-align: left;
  font-size: 7px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: #94A3B8;
  padding: 10px 8px;
  border-bottom: 2px solid #F1F5F9;
}
td {
  padding: 12px 8px;
  border-bottom: 1px solid #F8FAFC;
  font-size: 10px;
  color: #334155;
  vertical-align: top;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 7px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.sev-CRITICAL { background: #FEE2E2; color: #991B1B; }
.sev-HIGH { background: #FFEDD5; color: #9A3412; }
.sev-MODERATE { background: #FEF9C3; color: #854D0E; }
.sev-LOW { background: #DCFCE7; color: #166534; }
.sev-NONE { background: #F1F5F9; color: #475569; }

.footer-info {
  margin-top: 50px;
  padding-top: 20px;
  border-top: 1px solid #F1F5F9;
  font-size: 8px;
  color: #94A3B8;
  line-height: 1.6;
}
</style>
</head>
<body>

<div class="header">
  <div class="brand">
    <div class="brand-logo">+</div>
    <div class="brand-text">Talk To+ <span style="color:#94A3B8">/ BDaaS</span></div>
  </div>
  <div class="report-meta">
    {{ tenant_name }}<br>
    {{ generated_at }}<br>
    {{ window_label }}
  </div>
</div>

<div class="kicker">Executive Summary</div>
<h1>{{ headline }}</h1>
<p class="lede">{{ lede }}</p>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Global Risk Index</div>
    <div class="kpi-value">{{ gri.value }}</div>
    <div class="kpi-sub">Trend: {{ gri.trend }} / 4.0</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Active HIGH+ Risks</div>
    <div class="kpi-value">{{ gri.active }}</div>
    <div class="kpi-sub">Out of {{ gri.total }} validated</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Swarm Fragments</div>
    <div class="kpi-value">{{ swarm_count }}</div>
    <div class="kpi-sub">Anonymized signals</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Action Playbooks</div>
    <div class="kpi-value">{{ card_count }}</div>
    <div class="kpi-sub">{{ swarm_verified_count }} verified by swarm</div>
  </div>
</div>

<h2>Execution Risk Trend</h2>
<div class="trend-container">
  <div class="trend-bars">
    {% for p in trend %}
      <div class="trend-bar" style="height: {{ (p.value / 4 * 100) | round(0) }}%; opacity: {{ 0.3 + (loop.index / trend|length) * 0.7 }};"></div>
    {% endfor %}
  </div>
  <div class="trend-axis">
    <span>{{ trend[0].date }}</span>
    <span>Aggregated Risk Index (0.0 — 4.0)</span>
    <span>{{ trend[-1].date }}</span>
  </div>
</div>

<h2>Sovereignty Heatmap</h2>
<div class="heatmap-grid">
  {% for c in heatmap %}
  <div class="heat-card">
    <div class="heat-label">{{ c.label }}</div>
    <div class="heat-value">{{ c.level if c.count > 0 else '—' }}</div>
    <div class="progress-bg">
      <div class="progress-fill sev-{{ c.level }}" style="width: {{ (c.score / 4 * 100) | round(0) }}%;"></div>
    </div>
    <div style="font-size:7px; color:#94A3B8; margin-top:8px;">{{ c.count }} signals · Score {{ c.score }}</div>
  </div>
  {% endfor %}
</div>

<h2>Critical Oracle Alerts</h2>
{% if alerts %}
  {% for a in alerts %}
  <div class="alert-item">
    <div class="alert-header">
      <div class="alert-title">{{ a.title }}</div>
      <div class="badge sev-{{ a.severity }}">{{ a.severity }}</div>
    </div>
    <div class="alert-meta">{{ a.sector }} · Velocity +{{ a.velocity }}% · Confidence {{ (a.confidence * 100) | round(0) }}%</div>
    <div class="alert-desc">{{ a.description }}</div>
  </div>
  {% endfor %}
{% else %}
  <p style="font-size: 10px; color: #94A3B8; font-style: italic;">No high-priority anomalies detected in the current observation window.</p>
{% endif %}

<div style="page-break-before: always;"></div>

<h2>Recently Validated Signals</h2>
<table>
  <thead>
    <tr>
      <th style="width: 50%">Signal Detail</th>
      <th>Business Unit</th>
      <th>Risk Level</th>
      <th>Date</th>
    </tr>
  </thead>
  <tbody>
    {% for s in signals %}
    <tr>
      <td style="font-weight: 500;">{{ s.content_short }}</td>
      <td>{{ s.business_unit }}</td>
      <td><span class="badge sev-{{ s.risk }}">{{ s.risk }}</span></td>
      <td style="color: #64748B;">{{ s.when }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h2>Risk Severity Distribution</h2>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 10px;">
  <div>
    {% for d in distribution %}
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
      <div style="width: 8px; height: 8px; border-radius: 2px; background: {{ d.color }};"></div>
      <div style="flex: 1; font-size: 10px; font-weight: 600;">{{ d.name }}</div>
      <div style="font-size: 10px; color: #64748B;">{{ d.value }} signals ({{ d.percentage }}%)</div>
    </div>
    {% endfor %}
  </div>
  <div style="font-size: 9px; color: #64748B; background: #F8FAFC; padding: 16px; border-radius: 8px;">
    <strong>Methodology Note:</strong><br>
    The Global Risk Index (GRI) is calculated using time-decayed severity weights. Recent critical signals carry significantly higher weight than historical moderate items.
  </div>
</div>

<div class="footer-info">
  Generated by TALK TO+ BDaaS · Sovereign Edge Intelligence.<br>
  All data is processed within the tenant boundary. Cross-sector patterns are derived from anonymized swarm fragments.
  Scale: 0.0 (Minimal Risk) — 4.0 (Critical Failure Risk).
</div>

</body></html>"""


def render_executive_pdf(payload: dict) -> bytes:
    from jinja2 import Template
    from weasyprint import HTML
    html = Template(EXECUTIVE_REPORT_HTML).render(**payload)
    return HTML(string=html).write_pdf()
