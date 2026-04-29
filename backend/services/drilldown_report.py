"""
TALK TO+ BDaaS — Drill-down deep-dive PDF for a single bottleneck category.
Renders explainer + cross-sector data + tenant-specific signals + recommended playbook.
"""
EOH = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@page {
  size: A4;
  margin: 25mm 20mm 25mm 20mm;
  @bottom-left {
    content: "{{ tenant_name }} · Confidential · Deep Dive: {{ category_label }}";
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
  border-bottom: 1px solid #0F172A;
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

/* Boxes & Lists */
.highlight-box {
  background: #F8FAFC;
  border-left: 4px solid #0F172A;
  padding: 20px;
  margin: 20px 0;
  font-size: 11pt;
  color: #1E293B;
  line-height: 1.6;
}

.playbook-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.playbook-step {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  page-break-inside: avoid;
}
.step-num {
  width: 24px;
  height: 24px;
  background: #0F172A;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  shrink: 0;
}
.step-text {
  font-size: 10pt;
  color: #334155;
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

/* Badges & Tags */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 7px;
  font-weight: 800;
  text-transform: uppercase;
}
.sev-CRITICAL { background: #FEE2E2; color: #991B1B; }
.sev-HIGH { background: #FFEDD5; color: #9A3412; }
.sev-MODERATE { background: #FEF9C3; color: #854D0E; }
.sev-LOW { background: #DCFCE7; color: #166534; }

.tag-cloud {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.tag {
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 4px 10px;
  background: white;
  border: 1px solid #E2E8F0;
  border-radius: 4px;
  font-weight: 700;
  color: #64748B;
}

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
    Deep Dive Analysis<br>
    {{ generated_at }}
  </div>
</div>

<div class="kicker">{{ category_label }}</div>
<h1>Structural Deep Dive</h1>
<p class="lede">{{ explainer }}</p>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Tenant Signals</div>
    <div class="kpi-value">{{ tenant_count }}</div>
    <div class="kpi-sub">Avg Risk: {{ tenant_avg_weight }}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Swarm Fragments</div>
    <div class="kpi-value">{{ swarm_count }}</div>
    <div class="kpi-sub">{{ swarm_pct }}% of all data</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Affected Sectors</div>
    <div class="kpi-value">{{ sectors_count }}</div>
    <div class="kpi-sub">Global footprint</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Severity Level</div>
    <div class="kpi-value">{{ tenant_level }}</div>
    <div class="kpi-sub">Calculated rating</div>
  </div>
</div>

<h2>Strategic Context</h2>
<div class="highlight-box">
  {{ why_it_matters }}
</div>

<h2>Tenant-Specific Signals</h2>
{% if tenant_signals %}
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
    {% for s in tenant_signals %}
    <tr>
      <td style="font-weight: 500;">{{ s.content }}</td>
      <td>{{ s.business_unit }}</td>
      <td><span class="badge sev-{{ s.risk }}">{{ s.risk }}</span></td>
      <td style="color: #64748B;">{{ s.when }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% else %}
  <p style="font-size: 10px; color: #94A3B8; font-style: italic;">No specific signals recorded in this category for your tenant yet. Bottleneck is detected via cross-sector anomaly matching.</p>
{% endif %}

<h2>Cross-Sector Swarm Intelligence</h2>
<p style="font-size: 10px; color: #475569; margin-bottom: 12px;">Zero-knowledge fragments from peer organizations (anonymized patterns):</p>
<table>
  <thead>
    <tr>
      <th>Sector</th>
      <th>Fragment Count</th>
      <th>Avg Severity</th>
      <th>48h Velocity</th>
    </tr>
  </thead>
  <tbody>
    {% for r in cross_sector %}
    <tr>
      <td style="font-weight: 600;">{{ r.sector }}</td>
      <td style="font-family: monospace;">{{ r.count }}</td>
      <td><span class="badge sev-{{ r.severity }}">{{ r.severity }}</span></td>
      <td style="font-family: monospace; font-weight: 700; color: {{ '#DC2626' if r.velocity > 30 else '#0F172A' }};">+{{ r.velocity }}%</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<div style="page-break-before: always;"></div>

<h2>Recommended Intervention Playbook</h2>
<p style="font-size: 10px; color: #64748B; margin-bottom: 20px;">Swarm-validated success patterns for {{ category_label }} bottlenecks:</p>
<div class="playbook-list">
  {% for step in playbook %}
  <div class="playbook-step">
    <div class="step-num">{{ loop.index }}</div>
    <div class="step-text">{{ step }}</div>
  </div>
  {% endfor %}
</div>

<h2>Associated Market Sectors</h2>
<div class="tag-cloud">
  {% for s in related_sectors %}<span class="tag">{{ s }}</span>{% endfor %}
</div>

<div class="footer-info">
  Generated by TALK TO+ BDaaS · Sovereign Edge Architecture.<br>
  Cross-sector patterns are derived via cosine-clustering (threshold ≥0.55) on BAAI/bge-m3 embeddings.
  Raw qualitative content remains strictly within the originating tenant's boundary.
</div>

</body></html>"""


def render_drilldown_pdf(payload: dict) -> bytes:
    from jinja2 import Template
    from weasyprint import HTML
    return HTML(string=Template(EOH).render(**payload)).write_pdf()
