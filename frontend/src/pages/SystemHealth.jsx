import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';

export default function SystemHealth() {
  const { t } = useContext(AppCtx);
  const [sys, setSys] = useState(null);
  useEffect(() => {
    const load = () => http.get('/system/health').then(r => setSys(r.data));
    load(); const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  if (!sys) return <div className="text-sm text-slate-400">{t.loading}</div>;

  return (
    <div data-testid="system-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">{t.system.title}</h1>
          <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.system.subtitle}</div>
        </div>
        <div className={`px-4 py-2 rounded-sm border text-xs font-bold tracking-widest uppercase ${sys.overall === 'operational' ? 'sev-LOW' : 'sev-CRITICAL'}`}>
          {sys.overall === 'operational' ? t.system.operational : t.system.degraded}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {Object.entries(sys.services).map(([key, s]) => (
          <div key={key} className="tkp-card p-6" data-testid={`service-${key}`}>
            <div className="flex items-center justify-between mb-3">
              <div className="font-heading text-lg font-bold tracking-tight capitalize">{key.replace('_', ' ')}</div>
              <span className={`text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border rounded-sm ${['online', 'healthy', 'connected'].includes(s.status) ? 'sev-LOW' : 'sev-CRITICAL'}`}>
                {s.status}
              </span>
            </div>
            <div className="space-y-1.5 text-sm">
              {Object.entries(s).filter(([k]) => k !== 'status').map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{k}</span>
                  <span className="font-mono text-xs text-slate-700">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 text-[10px] text-slate-400 font-mono">
        Last update: {new Date(sys.timestamp).toLocaleString()} · {sys.version}
      </div>
    </div>
  );
}
