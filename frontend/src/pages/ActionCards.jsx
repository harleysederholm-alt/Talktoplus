import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { CheckCircle, Star } from '@phosphor-icons/react';

export default function ActionCards() {
  const { t } = useContext(AppCtx);
  const [cards, setCards] = useState([]);
  const load = () => http.get('/action-cards').then(r => setCards(r.data));
  useEffect(() => { load(); }, []);

  const score = async (id, n) => {
    await http.post(`/action-cards/${id}/impact?score=${n}`);
    load();
  };

  return (
    <div data-testid="actions-page">
      <div className="mb-6">
        <h1 className="font-heading text-4xl font-black tracking-tighter">{t.actions.title}</h1>
        <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.actions.subtitle}</div>
      </div>

      <div className="grid grid-cols-12 gap-6 stagger">
        {cards.length === 0 && <div className="col-span-12 text-sm text-slate-400">{t.empty}</div>}
        {cards.map(c => (
          <div key={c.id} className="col-span-12 md:col-span-6 tkp-card p-6" data-testid={`card-${c.id}`}>
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="font-heading text-lg font-bold tracking-tight">{c.title}</div>
              {c.swarm_verified && (
                <span className="sev-LOW border px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-widest uppercase flex items-center gap-1">
                  <CheckCircle size={10} weight="fill" />{t.actions.verified}
                </span>
              )}
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
              </div>
            )}

            <div className="border-t border-slate-200 pt-4 mt-4 flex items-center justify-between">
              <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.actions.impact}</div>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    data-testid={`score-${c.id}-${n}`}
                    onClick={() => score(c.id, n)}
                    className={`w-7 h-7 rounded-sm border transition-colors ${
                      (c.impact_score || 0) >= n ? 'bg-ink border-ink text-white' : 'bg-white border-slate-200 text-slate-400 hover:border-ink'
                    }`}>
                    <Star size={12} weight={(c.impact_score || 0) >= n ? 'fill' : 'regular'} className="mx-auto" />
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
