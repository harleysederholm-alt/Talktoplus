import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { CheckCircle, FilePdf, ShieldCheck, ArrowsClockwise, XCircle, ArrowUp, Play } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { tFmt } from '../i18n';

const STATUS_STYLES = {
  pending_validation: 'bg-amber-50 text-amber-800 border-amber-300',
  validated: 'bg-emerald-50 text-emerald-800 border-emerald-300',
  in_progress: 'bg-blue-50 text-blue-800 border-blue-300',
  dismissed: 'bg-slate-100 text-slate-600 border-slate-300',
  escalated: 'bg-red-50 text-red-700 border-red-300',
};

export default function ActionCards() {
  const { t, search, timeRange } = useContext(AppCtx);
  const [cards, setCards] = useState([]);
  const load = () => http.get('/action-cards').then(r => setCards(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const filtered = cards.filter(c => {
    const ageDays = (Date.now() - new Date(c.created_at).getTime()) / 86400000;
    if (ageDays > timeRange) return false;
    if (search) {
      const q = search.toLowerCase();
      return (c.title || '').toLowerCase().includes(q) ||
             (c.summary || '').toLowerCase().includes(q) ||
             (c.facilitator || '').toLowerCase().includes(q);
    }
    return true;
  });

  const score = async (id, n) => {
    await http.post(`/action-cards/${id}/impact?score=${n}`);
    toast.success(`Impact ${n}/10`);
    load();
  };

  const setStatus = async (id, status) => {
    try {
      await http.post(`/action-cards/${id}/status?status=${status}`);
      toast.success(`Status: ${t.actions[status] || status}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Error'); }
  };

  const downloadPdf = async (c) => {
    try {
      const r = await http.get(`/action-cards/${c.id}/export.pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url; a.download = `action-card-${c.id.slice(0, 8)}.pdf`; a.click();
      URL.revokeObjectURL(url);
      toast.success('PDF exported');
    } catch (e) { toast.error('Export failed'); }
  };

  return (
    <div data-testid="actions-page">
      <div className="mb-6">
        <h1 className="font-heading text-4xl font-black tracking-tighter">{t.actions.title}</h1>
        <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.actions.subtitle}</div>
      </div>

      <div className="grid grid-cols-12 gap-6 stagger">
        {filtered.length === 0 && <div className="col-span-12 text-sm text-slate-400">{search ? `No matches for "${search}"` : t.empty}</div>}
        {filtered.map(c => (
          <div key={c.id} className="col-span-12 md:col-span-6 tkp-card p-6" data-testid={`card-${c.id}`}>
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="min-w-0 flex-1">
                <div className="font-heading text-lg font-bold tracking-tight">{c.title}</div>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span className={`text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border rounded-sm ${STATUS_STYLES[c.status] || STATUS_STYLES.pending_validation}`}>
                    {t.actions[c.status] || c.status}
                  </span>
                  {c.swarm_verified && (
                    <span className="sev-LOW border px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-widest uppercase flex items-center gap-1">
                      <ShieldCheck size={10} weight="fill" />{t.actions.verified}
                      {c.swarm_verified_count > 0 && <span className="ml-1 font-mono">({c.swarm_verified_count})</span>}
                    </span>
                  )}
                  {c.facilitator && <span className="text-[10px] tracking-widest uppercase text-slate-500 font-mono">{c.facilitator}</span>}
                </div>
              </div>
              <button
                data-testid={`export-${c.id}`}
                onClick={() => downloadPdf(c)}
                className="px-2 py-1 text-[10px] font-bold tracking-widest uppercase border border-slate-200 rounded-sm hover:border-ink flex items-center gap-1 shrink-0"
                title="Export PDF"
              >
                <FilePdf size={12} weight="duotone" />{t.actions.pdf}
              </button>
            </div>

            <div className="text-sm text-slate-600 leading-relaxed mb-4">{c.summary}</div>

            <div className="border-t border-slate-200 pt-4">
              <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.actions.playbook}</div>
              <ol className="space-y-1.5 text-sm text-slate-700">
                {c.playbook.map((step, i) => <li key={i}>{step}</li>)}
              </ol>
            </div>

            {c.swarm_patterns_used?.length > 0 && (
              <div className="border-t border-slate-200 pt-4 mt-4">
                <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.actions.swarmUsed}</div>
                <ul className="text-xs text-slate-600 space-y-1">
                  {c.swarm_patterns_used.map((p, i) => <li key={i}>· {p}</li>)}
                </ul>
                <div className="text-[10px] text-slate-500 mt-2 italic">{tFmt(t.actions.verifiedBy, { n: c.swarm_verified_count || 7 })}</div>
              </div>
            )}

            {/* Status actions */}
            <div className="border-t border-slate-200 pt-4 mt-4 flex flex-wrap items-center gap-2">
              {c.status !== 'validated' && (
                <button data-testid={`act-validate-${c.id}`} onClick={() => setStatus(c.id, 'validated')} className="px-3 py-1.5 text-[11px] font-bold tracking-widest uppercase rounded-sm bg-emerald-600 text-white border border-emerald-600 flex items-center gap-1 hover:bg-emerald-700">
                  <CheckCircle size={12} weight="bold" />{t.actions.validate}
                </button>
              )}
              {c.status !== 'in_progress' && c.status !== 'dismissed' && (
                <button data-testid={`act-start-${c.id}`} onClick={() => setStatus(c.id, 'in_progress')} className="px-3 py-1.5 text-[11px] font-bold tracking-widest uppercase rounded-sm bg-blue-600 text-white border border-blue-600 flex items-center gap-1 hover:bg-blue-700">
                  <Play size={12} weight="fill" />{t.actions.start}
                </button>
              )}
              {c.status !== 'escalated' && c.status !== 'dismissed' && (
                <button data-testid={`act-escalate-${c.id}`} onClick={() => setStatus(c.id, 'escalated')} className="px-3 py-1.5 text-[11px] font-bold tracking-widest uppercase rounded-sm bg-red-600 text-white border border-red-600 flex items-center gap-1 hover:bg-red-700">
                  <ArrowUp size={12} weight="bold" />{t.actions.escalate}
                </button>
              )}
              {c.status !== 'dismissed' && (
                <button data-testid={`act-dismiss-${c.id}`} onClick={() => setStatus(c.id, 'dismissed')} className="px-3 py-1.5 text-[11px] font-bold tracking-widest uppercase rounded-sm border border-slate-200 text-slate-600 flex items-center gap-1 hover:border-ink">
                  <XCircle size={12} />{t.actions.dismiss}
                </button>
              )}
            </div>

            {/* Impact 1-10 */}
            <div className="border-t border-slate-200 pt-4 mt-4 flex items-center justify-between">
              <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.actions.impact}</div>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                  <button
                    key={n}
                    data-testid={`score-${c.id}-${n}`}
                    onClick={() => score(c.id, n)}
                    title={`${n}/10`}
                    className={`w-5 h-6 rounded-sm border transition-colors text-[10px] font-bold ${
                      (c.impact_score || 0) >= n ? 'bg-ink border-ink text-white' : 'bg-white border-slate-200 text-slate-400 hover:border-ink'
                    }`}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
