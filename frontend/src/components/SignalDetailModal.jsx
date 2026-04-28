import React from 'react';
import { X } from '@phosphor-icons/react';

const STATUS_COLORS = { CRITICAL: '#DC2626', HIGH: '#EA580C', MODERATE: '#CA8A04', LOW: '#16A34A' };

export default function SignalDetailModal({ signal, onClose, t }) {
  if (!signal) return null;
  const sev = signal.override_risk_level || signal.risk_level || 'MODERATE';
  return (
    <div
      data-testid="signal-detail-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-sm w-full max-w-3xl shadow-2xl border border-slate-200 max-h-[88vh] overflow-y-auto animate-fade-up">
        <div className="flex items-start justify-between p-6 border-b border-slate-200 sticky top-0 bg-white z-10">
          <div className="flex-1 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <span className={`sev-${sev} text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border rounded-sm`}>{sev}</span>
              <span className="text-[10px] tracking-widest uppercase text-slate-500 font-mono">{signal.business_unit}</span>
              <span className="text-[10px] tracking-widest uppercase text-slate-500 font-mono">· {signal.source}</span>
              <span className="text-[10px] tracking-widest uppercase text-slate-500 font-mono">· {signal.status}</span>
            </div>
            <div className="font-heading text-2xl font-black tracking-tighter">{t.decision.signal}</div>
          </div>
          <button data-testid="signal-detail-close" onClick={onClose} className="text-slate-400 hover:text-ink"><X size={20} /></button>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.decision.signal}</div>
            <div className="text-base text-slate-800 leading-relaxed">{signal.content}</div>
            <div className="mt-2 text-[11px] font-mono text-slate-500">
              {signal.author} · {new Date(signal.submitted_at).toLocaleString()}
            </div>
          </div>

          {signal.summary && (
            <div className="bg-slate-50 p-4 border-l-4" style={{ borderColor: STATUS_COLORS[sev] }}>
              <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-1">{t.decision.aiAnalysis}</div>
              <div className="text-sm text-slate-700">{signal.summary}</div>
              <div className="text-[10px] text-slate-500 mt-2 font-mono">
                Confidence {Math.round((signal.confidence || 0) * 100)}% · {signal.category}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {signal.execution_gaps?.length > 0 && (
              <div>
                <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.decision.gaps}</div>
                <ul className="text-sm space-y-1.5">
                  {signal.execution_gaps.map((g, i) => <li key={i}>• {g}</li>)}
                </ul>
              </div>
            )}
            {signal.hidden_assumptions?.length > 0 && (
              <div>
                <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.decision.assumptions}</div>
                <ul className="text-sm space-y-1.5">
                  {signal.hidden_assumptions.map((g, i) => <li key={i}>• {g}</li>)}
                </ul>
              </div>
            )}
            {signal.facilitator_questions?.length > 0 && (
              <div>
                <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{t.decision.questions}</div>
                <ul className="text-sm space-y-1.5">
                  {signal.facilitator_questions.map((g, i) => <li key={i}>• {g}</li>)}
                </ul>
              </div>
            )}
          </div>

          {signal.validated_by && (
            <div className="border-t border-slate-200 pt-4 text-[11px] font-mono text-slate-500">
              {t.actions.facilitator}: <span className="font-semibold text-slate-700">{signal.validated_by}</span>
              {signal.validated_at && <> · {new Date(signal.validated_at).toLocaleString()}</>}
              {signal.validation_note && <div className="mt-2 italic text-slate-600">"{signal.validation_note}"</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
