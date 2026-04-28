import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, Area, AreaChart, PieChart, Pie, Cell } from 'recharts';
import { Link } from 'react-router-dom';
import { CaretRight, Users, TrendUp, UserCircle, WarningOctagon, Waveform } from '@phosphor-icons/react';

const STATUS_COLORS = { CRITICAL: '#EF4444', HIGH: '#F97316', MODERATE: '#EAB308', LOW: '#94A3B8' };

const PageHead = ({ title, subtitle }) => (
  <div className="mb-6">
    <h1 className="font-heading text-4xl font-black tracking-tighter">{title}</h1>
    <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{subtitle}</div>
  </div>
);

const Card = ({ className = '', children, testId }) => (
  <div data-testid={testId} className={`tkp-card p-6 ${className}`}>{children}</div>
);

const CardTitle = ({ title, subtitle, actions }) => (
  <div className="flex items-start justify-between mb-5">
    <div>
      <div className="font-heading text-xl font-bold tracking-tight">{title}</div>
      {subtitle && <div className="text-xs text-slate-500 mt-1">{subtitle}</div>}
    </div>
    {actions}
  </div>
);

const LevelBadge = ({ level }) => (
  <span className={`sev-${level} text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border rounded-sm`}>{level}</span>
);

export default function Boardroom() {
  const { t } = useContext(AppCtx);
  const [heat, setHeat] = useState({});
  const [trend, setTrend] = useState([]);
  const [dist, setDist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [bottlenecks, setBottlenecks] = useState([]);
  const [signals, setSignals] = useState([]);
  const [sys, setSys] = useState(null);

  useEffect(() => {
    Promise.all([
      http.get('/analytics/heatmap'),
      http.get('/analytics/risk-trend?days=7'),
      http.get('/analytics/distribution'),
      http.get('/oracle/alerts'),
      http.get('/swarm/bottlenecks'),
      http.get('/signals?limit=5'),
      http.get('/system/health'),
    ]).then(([h, tr, d, al, bn, sg, sh]) => {
      setHeat(h.data); setTrend(tr.data); setDist(d.data);
      setAlerts(al.data); setBottlenecks(bn.data);
      setSignals(sg.data.filter(s => s.status !== 'pending').slice(0, 4));
      setSys(sh.data);
    }).catch(() => {});
  }, []);

  const totalRisks = dist.reduce((a, x) => a + x.value, 0);
  const timeAgo = (iso) => {
    const ms = Date.now() - new Date(iso).getTime();
    const m = Math.floor(ms / 60000);
    if (m < 60) return `${m} min ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h} hour${h > 1 ? 's' : ''} ago`;
    return `${Math.floor(h / 24)}d ago`;
  };

  return (
    <div data-testid="boardroom-page">
      <PageHead title={t.boardroom.title} subtitle={t.boardroom.subtitle} />

      <div className="grid grid-cols-12 gap-6 stagger">
        {/* Executive Heatmap — spans left 8 */}
        <Card className="col-span-12 lg:col-span-8" testId="heatmap-card">
          <CardTitle
            title={t.boardroom.heatmap}
            subtitle={t.boardroom.heatmapSub}
            actions={
              <div className="flex items-center gap-2">
                <select data-testid="heatmap-bu-filter" className="tkp-input w-auto text-xs">
                  <option>{t.allBusinessUnits}</option>
                </select>
                <button data-testid="heatmap-export" className="tkp-btn-primary">{t.export}</button>
              </div>
            }
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { key: 'resources', label: t.boardroom.resources, icon: Users, data: heat.resources },
              { key: 'capabilities', label: t.boardroom.capabilities, icon: TrendUp, data: heat.capabilities },
              { key: 'engagement', label: t.boardroom.engagement, icon: UserCircle, data: heat.engagement },
            ].map(({ key, label, icon: Icon, data }) => {
              const level = data?.level || 'LOW';
              return (
                <div key={key} data-testid={`heat-${key}`} className="border border-slate-200 rounded-sm p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-[10px] tracking-[0.2em] uppercase text-slate-500 font-bold">{label}</div>
                      <div className="font-heading text-3xl font-black tracking-tighter mt-3">{level}</div>
                    </div>
                    <div className={`w-10 h-10 rounded-full sev-${level} border flex items-center justify-center`}>
                      <Icon size={16} weight="duotone" />
                    </div>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full mt-4 overflow-hidden">
                    <div className={`h-full bar-${level}`} style={{ width: `${Math.min((data?.score || 1) / 4 * 100, 100)}%` }} />
                  </div>
                  <div className="mt-3 flex items-baseline justify-between">
                    <span className="font-heading text-2xl font-bold">{data?.score ?? '—'}</span>
                    <span className="text-[10px] tracking-widest uppercase text-slate-500">{t.boardroom.riskScore}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Oracle Alerts — right column */}
        <Card className="col-span-12 lg:col-span-4" testId="oracle-card">
          <CardTitle title={t.boardroom.oracle} subtitle={t.boardroom.oracleSub} />
          <div className="space-y-5">
            {alerts.length === 0 && <div className="text-sm text-slate-400">—</div>}
            {alerts.slice(0, 2).map(a => (
              <div key={a.id} className="pb-5 border-b border-slate-200 last:border-none last:pb-0" data-testid={`oracle-alert-${a.id}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-7 h-7 rounded-full sev-${a.severity} border flex items-center justify-center`}>
                      <WarningOctagon size={14} weight="duotone" />
                    </div>
                    <div className="font-heading text-sm font-bold tracking-tight">{a.title}</div>
                  </div>
                  <span className="text-[10px] tracking-widest uppercase text-slate-400">{a.sector}</span>
                </div>
                <div className="text-xs text-slate-600 leading-relaxed mb-3">{a.description}</div>
                <div className="grid grid-cols-3 gap-2 text-[10px] tracking-widest uppercase text-slate-500 font-bold">
                  <div>{t.boardroom.velocity}<div className="text-ink font-mono text-sm mt-1 normal-case tracking-normal">+{a.velocity}%</div></div>
                  <div>{t.boardroom.zscore}<div className="text-ink font-mono text-sm mt-1 normal-case tracking-normal">{a.z_score}</div></div>
                  <div>{t.boardroom.confidence}<div className="text-ink font-mono text-sm mt-1 normal-case tracking-normal">{Math.round(a.confidence * 100)}%</div></div>
                </div>
                <div className="mt-2 h-1 bg-slate-100 rounded">
                  <div className={`h-full bar-${a.severity} rounded`} style={{ width: `${Math.round(a.confidence * 100)}%` }} />
                </div>
                <div className="text-[10px] text-slate-400 mt-2 font-mono">{timeAgo(a.created_at)}</div>
              </div>
            ))}
          </div>
        </Card>

        {/* Trend — spans 8 */}
        <Card className="col-span-12 lg:col-span-5" testId="trend-card">
          <CardTitle
            title={t.boardroom.trend}
            subtitle={t.boardroom.trendSub}
            actions={
              <select data-testid="trend-range" className="tkp-input w-auto text-xs">
                <option>7 Days</option>
              </select>
            }
          />
          <div className="flex items-baseline gap-3 mb-4">
            <span className="font-heading text-5xl font-black tracking-tighter">
              {trend[trend.length - 1]?.value ?? '—'}
            </span>
            <span className="text-[11px] tracking-widest uppercase text-emerald-600 font-bold">{t.boardroom.stable}</span>
          </div>
          <div className="h-56 -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0A0A0A" stopOpacity="0.15" />
                    <stop offset="100%" stopColor="#0A0A0A" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} />
                <YAxis domain={[0, 4]} tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} width={22} />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 2, border: '1px solid #E2E8F0' }} />
                <Area type="monotone" dataKey="value" stroke="#0A0A0A" strokeWidth={2} fill="url(#g)" dot={{ r: 3, fill: '#0A0A0A' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Risk distribution — 3 */}
        <Card className="col-span-12 lg:col-span-3" testId="dist-card">
          <CardTitle title={t.boardroom.distribution} subtitle={t.boardroom.distributionSub} />
          <div className="relative">
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dist} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={3} stroke="none">
                    {dist.map((e, i) => <Cell key={i} fill={STATUS_COLORS[e.name]} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <div className="font-heading text-3xl font-black tracking-tighter">{totalRisks}</div>
              <div className="text-[10px] tracking-widest uppercase text-slate-500 mt-1">{t.boardroom.total}</div>
            </div>
          </div>
          <div className="mt-4 space-y-1.5">
            {dist.map(d => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ background: STATUS_COLORS[d.name] }} />
                  <span className="font-medium">{d.name.charAt(0) + d.name.slice(1).toLowerCase()}</span>
                </div>
                <span className="font-mono text-slate-500">{d.value} ({d.percentage}%)</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Universal Bottlenecks — 4 */}
        <Card className="col-span-12 lg:col-span-4" testId="bottlenecks-card">
          <CardTitle title={t.boardroom.universal} subtitle={t.boardroom.universalSub} />
          <div className="space-y-4">
            {bottlenecks.length === 0 && <div className="text-sm text-slate-400">—</div>}
            {bottlenecks.map(b => (
              <div key={b.id} data-testid={`bottleneck-${b.id}`}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="text-sm font-semibold">{b.label.split(' / ')[0]}</div>
                  <div className="text-xs font-mono text-slate-600">{b.percentage}%</div>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-sm overflow-hidden">
                  <div className="h-full bg-ink" style={{ width: `${Math.min(b.percentage, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
          <Link to="/global" className="mt-6 block text-center py-2 text-xs font-bold tracking-widest uppercase border border-slate-200 rounded-sm hover:border-ink" data-testid="view-bottlenecks">
            {t.viewAllBottlenecks}
          </Link>
        </Card>

        {/* Recent validated signals — 8 */}
        <Card className="col-span-12 lg:col-span-8" testId="recent-signals-card">
          <CardTitle title={t.boardroom.recent} subtitle={t.boardroom.recentSub} />
          <table className="w-full">
            <thead>
              <tr className="text-[10px] tracking-widest uppercase text-slate-500 font-bold border-b border-slate-200">
                <th className="text-left pb-3">{t.decision.signal}</th>
                <th className="text-left pb-3">{t.signals.businessUnit}</th>
                <th className="text-left pb-3">{t.decision.riskLevel}</th>
                <th className="text-left pb-3">Validated by</th>
                <th className="text-left pb-3">Time</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {signals.map(s => (
                <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50 text-sm" data-testid={`signal-row-${s.id}`}>
                  <td className="py-3 pr-4 truncate max-w-[280px]">{s.content.slice(0, 48)}…</td>
                  <td className="py-3 pr-4 text-slate-600">{s.business_unit}</td>
                  <td className="py-3 pr-4"><LevelBadge level={s.override_risk_level || s.risk_level} /></td>
                  <td className="py-3 pr-4 text-slate-600">{s.validated_by || '—'}</td>
                  <td className="py-3 pr-4 text-slate-500 font-mono text-xs">{s.validated_at ? timeAgo(s.validated_at) : timeAgo(s.submitted_at)}</td>
                  <td><CaretRight size={14} className="text-slate-400" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* System status — 4 */}
        <Card className="col-span-12 lg:col-span-4" testId="system-status-card">
          <CardTitle title={t.boardroom.systemStatus} subtitle={t.boardroom.systemStatusSub} />
          <div className="grid grid-cols-4 gap-3">
            {sys && [
              { k: t.boardroom.localAI, v: sys.services.local_ai.status, ok: sys.services.local_ai.status === 'online' },
              { k: t.boardroom.database, v: sys.services.database.status === 'healthy' ? t.boardroom.healthy : 'down', ok: sys.services.database.status === 'healthy' },
              { k: t.boardroom.vectorDB, v: sys.services.vector_db.status === 'healthy' ? t.boardroom.healthy : 'down', ok: sys.services.vector_db.status === 'healthy' },
              { k: t.boardroom.mothership, v: t.boardroom.connected, ok: true },
            ].map((s, i) => (
              <div key={i} className="text-center" data-testid={`status-${i}`}>
                <div className="w-10 h-10 mx-auto rounded-full border border-slate-200 flex items-center justify-center">
                  <Waveform size={16} weight="duotone" className="text-slate-600" />
                </div>
                <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mt-2">{s.k}</div>
                <div className={`text-[11px] font-semibold mt-0.5 flex items-center justify-center gap-1 ${s.ok ? 'text-emerald-600' : 'text-red-600'}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${s.ok ? 'bg-emerald-500' : 'bg-red-500'}`} />{s.v}
                </div>
              </div>
            ))}
          </div>
          <Link to="/system" className="mt-6 block text-center py-2 text-xs font-bold tracking-widest uppercase border border-slate-200 rounded-sm hover:border-ink" data-testid="view-system">
            {t.viewSystemHealth}
          </Link>
        </Card>
      </div>
    </div>
  );
}
