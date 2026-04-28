import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { CheckCircle, XCircle, ArrowsClockwise } from '@phosphor-icons/react';

const LevelBadge = ({ level }) => (
  <span className={`sev-${level} text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border rounded-sm`}>{level}</span>
);

export default function DecisionHub() {
  const { t } = useContext(AppCtx);
  const [pending, setPending] = useState([]);
  const [active, setActive] = useState(null);
  const [mode, setMode] = useState('validate');
  const [note, setNote] = useState('');
  const [override, setOverride] = useState('HIGH');
  const [busy, setBusy] = useState(false);

  const load = () => http.get('/signals?status_=pending').then(r => {
    setPending(r.data);
    if (r.data.length > 0) setActive(r.data[0]);
    else setActive(null);
  }).catch(() => {});
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!active) return;
    setBusy(true);
    try {
      const body = { decision: mode, note: note || null };
      if (mode === 'override') body.override_risk_level = override;
      await http.post(`/signals/${active.id}/validate`, body);
      setNote('');
      await load();
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="decision-page">
      <div className="mb-6">
        <h1 className="font-heading text-4xl font-black tracking-tighter">{t.decision.title}</h1>
        <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.decision.subtitle}</div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-4 tkp-card p-0 overflow-hidden" data-testid="pending-list">
          <div className="p-5 border-b border-slate-200">
            <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.decision.pending}</div>
            <div className="font-heading text-3xl font-black tracking-tighter mt-1">{pending.length}</div>
          </div>
          <div className="max-h-[600px] overflow-y-auto">
            {pending.length === 0 && <div className="p-5 text-sm text-slate-400">{t.decision.noPending}</div>}
            {pending.map(s => (
              <button
                key={s.id}
                data-testid={`pending-${s.id}`}
                onClick={() => setActive(s)}
                className={`w-full text-left p-5 border-b border-slate-100 hover:bg-slate-50 ${active?.id === s.id ? 'bg-slate-50 border-l-4 border-l-ink' : ''}`}>
                <div className="flex items-center gap-2 mb-1">
                  <LevelBadge level={s.risk_level || 'MODERATE'} />
                  <span className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{s.business_unit}</span>
                </div>
                <div className="text-sm line-clamp-2">{s.content}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="col-span-12 lg:col-span-8">
          {!active ? (
            <div className="tkp-card p-8 text-center text-slate-400">{t.decision.noPending}</div>
          ) : (
            <div className="tkp-card p-8 space-y-6" data-testid="active-signal">
              <div>
                <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.decision.signal}</div>
                <div className="text-base text-slate-800 leading-relaxed mt-2">{active.content}</div>
                <div className="mt-2 text-[11px] font-mono text-slate-500">
                  {active.business_unit} · {active.author} · {active.source}
                </div>
              </div>

              <div className="border-t border-slate-200 pt-6">
                <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.decision.aiAnalysis}</div>
                <div className="flex items-center gap-3 mt-3">
                  <LevelBadge level={active.risk_level || 'MODERATE'} />
                  <span className="text-xs font-mono text-slate-500">confidence {Math.round((active.confidence || 0) * 100)}%</span>
                  {active.category && <span className="text-[10px] tracking-widest uppercase font-mono text-slate-500">· {active.category}</span>}
                </div>
                {active.summary && <div className="text-sm text-slate-700 mt-3 italic">{active.summary}</div>}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 border-t border-slate-200 pt-6">
                <div>
                  <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.decision.gaps}</div>
                  <ul className="text-sm space-y-1.5">
                    {(active.execution_gaps || []).map((g, i) => <li key={i}>• {g}</li>)}
                  </ul>
                </div>
                <div>
                  <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.decision.assumptions}</div>
                  <ul className="text-sm space-y-1.5">
                    {(active.hidden_assumptions || []).map((g, i) => <li key={i}>• {g}</li>)}
                  </ul>
                </div>
                <div>
                  <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.decision.questions}</div>
                  <ul className="text-sm space-y-1.5">
                    {(active.facilitator_questions || []).map((g, i) => <li key={i}>• {g}</li>)}
                  </ul>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-6 space-y-4">
                <div className="flex gap-2 flex-wrap">
                  {[
                    { k: 'validate', l: t.decision.validate, Icon: CheckCircle, cls: 'bg-emerald-600 text-white border-emerald-600' },
                    { k: 'override', l: t.decision.override, Icon: ArrowsClockwise, cls: 'bg-amber-500 text-white border-amber-500' },
                    { k: 'in_progress', l: t.decision.inProgress, Icon: ArrowsClockwise, cls: 'bg-blue-600 text-white border-blue-600' },
                    { k: 'escalate', l: t.decision.escalate, Icon: ArrowsClockwise, cls: 'bg-red-600 text-white border-red-600' },
                    { k: 'dismiss', l: t.decision.dismiss, Icon: XCircle, cls: 'bg-slate-700 text-white border-slate-700' },
                  ].map(({ k, l, Icon, cls }) => (
                    <button
                      key={k}
                      data-testid={`decision-${k}`}
                      onClick={() => setMode(k)}
                      className={`px-3 py-2 text-xs font-bold tracking-widest uppercase rounded-sm border flex items-center gap-2 ${mode === k ? cls : 'bg-white text-slate-600 border-slate-200 hover:border-ink'}`}>
                      <Icon size={14} />{l}
                    </button>
                  ))}
                </div>
                {mode === 'override' && (
                  <div>
                    <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.decision.overrideTo}</label>
                    <select data-testid="override-level" value={override} onChange={e => setOverride(e.target.value)} className="tkp-input mt-2 w-auto">
                      <option>LOW</option><option>MODERATE</option><option>HIGH</option><option>CRITICAL</option>
                    </select>
                  </div>
                )}
                <div>
                  <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.decision.note}</label>
                  <textarea data-testid="decision-note" value={note} onChange={e => setNote(e.target.value)} rows={2} className="tkp-input mt-2" />
                </div>
                <button data-testid="decision-submit" onClick={submit} disabled={busy} className="tkp-btn-primary">
                  {busy ? '…' : t.decision.submit}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
