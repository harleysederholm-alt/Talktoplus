import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { ArrowsClockwise } from '@phosphor-icons/react';

export default function GlobalIntel() {
  const { t, user } = useContext(AppCtx);
  const [bn, setBn] = useState([]);
  const [frags, setFrags] = useState(0);
  const [alerts, setAlerts] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = () => Promise.all([
    http.get('/swarm/bottlenecks'),
    http.get('/swarm/fragments/count'),
    http.get('/oracle/alerts'),
  ]).then(([b, f, a]) => { setBn(b.data); setFrags(f.data.count); setAlerts(a.data); });

  useEffect(() => { load(); }, []);

  const recompute = async () => {
    setBusy(true);
    try { await http.post('/swarm/recompute'); await load(); } finally { setBusy(false); }
  };

  return (
    <div data-testid="global-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">{t.global.title}</h1>
          <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.global.subtitle}</div>
        </div>
        {user?.role === 'super_admin' && (
          <button onClick={recompute} disabled={busy} className="tkp-btn-primary flex items-center gap-2" data-testid="recompute-btn">
            <ArrowsClockwise size={14} weight="bold" />{t.global.recompute}
          </button>
        )}
      </div>

      <div className="grid grid-cols-12 gap-6 mb-6">
        <div className="col-span-6 md:col-span-3 tkp-card p-6" data-testid="stat-fragments">
          <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.global.fragments}</div>
          <div className="font-heading text-4xl font-black tracking-tighter mt-2">{frags}</div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">Zero-Knowledge anonymized vectors</div>
        </div>
        <div className="col-span-6 md:col-span-3 tkp-card p-6" data-testid="stat-clusters">
          <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.global.clusters}</div>
          <div className="font-heading text-4xl font-black tracking-tighter mt-2">{bn.length}</div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">Greedy cosine ≥ 0.55</div>
        </div>
        <div className="col-span-12 md:col-span-6 tkp-card p-6" data-testid="stat-alerts">
          <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">Oracle signals</div>
          <div className="flex items-baseline gap-3 mt-2">
            <span className="font-heading text-4xl font-black tracking-tighter">{alerts.length}</span>
            <span className="text-xs text-slate-500">active predictions</span>
          </div>
        </div>
      </div>

      <div className="tkp-card p-6">
        <div className="font-heading text-xl font-bold tracking-tight mb-4">{t.global.clusters}</div>
        <div className="space-y-5">
          {bn.length === 0 && <div className="text-sm text-slate-400">{t.empty}</div>}
          {bn.map(b => (
            <div key={b.id} className="border-b border-slate-100 pb-5 last:border-none" data-testid={`cluster-${b.id}`}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-semibold text-base">{b.label}</div>
                  <div className="text-[10px] tracking-widest uppercase text-slate-500 font-mono mt-0.5">
                    {b.fragment_count} fragments · {t.global.sectorsAffected}: {b.sectors_affected.join(', ')}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-heading text-2xl font-black tracking-tighter">{b.percentage}%</div>
                  <div className="text-[10px] tracking-widest uppercase text-slate-500 font-mono">avg weight {b.avg_risk_weight}</div>
                </div>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-sm overflow-hidden">
                <div className="h-full bg-ink" style={{ width: `${Math.min(b.percentage, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
