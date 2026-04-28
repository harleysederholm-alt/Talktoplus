import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { Trash, Plus } from '@phosphor-icons/react';

export default function StrategyRAG() {
  const { t } = useContext(AppCtx);
  const [docs, setDocs] = useState([]);
  const [form, setForm] = useState({ title: '', content: '' });
  const [busy, setBusy] = useState(false);

  const load = () => http.get('/strategy-docs').then(r => setDocs(r.data));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await http.post('/strategy-docs', form); setForm({ title: '', content: '' }); await load(); }
    finally { setBusy(false); }
  };
  const del = async (id) => { await http.delete(`/strategy-docs/${id}`); load(); };

  return (
    <div data-testid="rag-page">
      <div className="mb-6">
        <h1 className="font-heading text-4xl font-black tracking-tighter">{t.rag.title}</h1>
        <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.rag.subtitle}</div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-5 tkp-card p-6">
          <div className="font-heading text-lg font-bold mb-4">{t.rag.add}</div>
          <form onSubmit={submit} className="space-y-4" data-testid="rag-form">
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.rag.title2}</label>
              <input data-testid="rag-title" required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className="tkp-input mt-2" />
            </div>
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.rag.content}</label>
              <textarea data-testid="rag-content" required value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} rows={8} className="tkp-input mt-2" />
            </div>
            <button data-testid="rag-submit" disabled={busy} className="tkp-btn-primary flex items-center gap-2">
              <Plus size={14} weight="bold" />{busy ? '…' : t.rag.add}
            </button>
          </form>
        </div>

        <div className="col-span-12 lg:col-span-7 tkp-card p-0 overflow-hidden">
          <div className="p-5 border-b border-slate-200 text-[10px] tracking-widest uppercase text-slate-500 font-bold">
            {docs.length} documents
          </div>
          {docs.length === 0 && <div className="p-6 text-sm text-slate-400">{t.rag.empty}</div>}
          <div className="divide-y divide-slate-100">
            {docs.map(d => (
              <div key={d.id} className="p-5" data-testid={`rag-doc-${d.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">{d.title}</div>
                    <div className="text-[10px] tracking-widest uppercase text-slate-500 font-mono mt-1">
                      {d.chunks} {t.rag.chunks} · {d.uploaded_by}
                    </div>
                  </div>
                  <button onClick={() => del(d.id)} className="text-slate-400 hover:text-red-600" data-testid={`rag-delete-${d.id}`}>
                    <Trash size={14} />
                  </button>
                </div>
                <div className="text-xs text-slate-600 mt-2 line-clamp-2">{d.content}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
