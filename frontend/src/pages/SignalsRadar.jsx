import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { Plus } from '@phosphor-icons/react';

const LevelBadge = ({ level }) => (
  <span className={`sev-${level} text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border rounded-sm`}>{level}</span>
);

export default function SignalsRadar() {
  const { t } = useContext(AppCtx);
  const [signals, setSignals] = useState([]);
  const [filter, setFilter] = useState('all');
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ content: '', business_unit: 'Engineering' });
  const [busy, setBusy] = useState(false);

  const load = () => {
    const q = filter === 'all' ? '' : `?status_=${filter}`;
    http.get(`/signals${q}`).then(r => setSignals(r.data)).catch(() => {});
  };
  useEffect(load, [filter]);

  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      await http.post('/signals', form);
      setForm({ content: '', business_unit: 'Engineering' });
      setShowNew(false);
      setTimeout(load, 800); // give AI a beat
    } finally { setBusy(false); }
  };

  const filters = [
    { k: 'all', l: t.signals.filterAll },
    { k: 'pending', l: t.signals.filterPending },
    { k: 'validated', l: t.signals.filterValidated },
    { k: 'dismissed', l: t.signals.filterDismissed },
  ];

  const timeAgo = (iso) => {
    const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    return h < 24 ? `${h}h` : `${Math.floor(h / 24)}d`;
  };

  return (
    <div data-testid="signals-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">{t.signals.title}</h1>
          <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.signals.subtitle}</div>
        </div>
        <button data-testid="new-signal-btn" onClick={() => setShowNew(!showNew)} className="tkp-btn-primary flex items-center gap-2">
          <Plus size={14} weight="bold" />{t.signals.newSignal}
        </button>
      </div>

      {showNew && (
        <div className="tkp-card p-6 mb-6" data-testid="new-signal-form">
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.signals.content}</label>
              <textarea data-testid="new-signal-content" required value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} rows={4} className="tkp-input mt-2" />
            </div>
            <div className="max-w-xs">
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.signals.businessUnit}</label>
              <input data-testid="new-signal-bu" required value={form.business_unit} onChange={e => setForm({ ...form, business_unit: e.target.value })} className="tkp-input mt-2" />
            </div>
            <button data-testid="new-signal-submit" disabled={busy} className="tkp-btn-primary">{busy ? '…' : t.signals.submit}</button>
          </form>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        {filters.map(f => (
          <button
            key={f.k}
            data-testid={`filter-${f.k}`}
            onClick={() => setFilter(f.k)}
            className={`px-3 py-1.5 text-xs font-bold tracking-widest uppercase rounded-sm border transition-colors ${
              filter === f.k ? 'bg-ink text-white border-ink' : 'bg-white text-slate-600 border-slate-200 hover:border-ink'
            }`}>
            {f.l}
          </button>
        ))}
      </div>

      <div className="tkp-card divide-y divide-slate-100">
        {signals.length === 0 && <div className="p-6 text-sm text-slate-400">{t.empty}</div>}
        {signals.map(s => (
          <div key={s.id} className="p-5 hover:bg-slate-50" data-testid={`signal-${s.id}`}>
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{s.business_unit}</span>
                  <span className="text-[10px] text-slate-400">·</span>
                  <span className="text-[10px] tracking-widest uppercase text-slate-500 font-mono">{s.source}</span>
                  <span className="text-[10px] text-slate-400">·</span>
                  <span className="text-[10px] font-mono text-slate-400">{timeAgo(s.submitted_at)} ago</span>
                </div>
                <div className="text-sm text-slate-800 leading-relaxed">{s.content}</div>
                {s.summary && <div className="text-xs text-slate-500 mt-2 italic">{s.summary}</div>}
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <LevelBadge level={s.override_risk_level || s.risk_level || 'MODERATE'} />
                <span className="text-[10px] tracking-widest uppercase font-mono text-slate-500">{s.status}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
