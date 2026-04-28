import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { Plus } from '@phosphor-icons/react';

export default function Tenants() {
  const { t, user } = useContext(AppCtx);
  const [tenants, setTenants] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ name: '', sector: '', description: '' });
  const load = () => http.get('/tenants').then(r => setTenants(r.data));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    try { await http.post('/tenants', form); setForm({ name: '', sector: '', description: '' }); setShow(false); load(); } catch (e) { alert(e?.response?.data?.detail); }
  };

  const isAdmin = user?.role === 'super_admin';

  return (
    <div data-testid="tenants-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">{t.tenants.title}</h1>
          <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.tenants.subtitle}</div>
        </div>
        {isAdmin && (
          <button onClick={() => setShow(!show)} className="tkp-btn-primary flex items-center gap-2" data-testid="new-tenant-btn">
            <Plus size={14} weight="bold" />{t.tenants.add}
          </button>
        )}
      </div>

      {show && (
        <form onSubmit={submit} className="tkp-card p-6 mb-6 grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="new-tenant-form">
          <div>
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.tenants.name}</label>
            <input required data-testid="tenant-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="tkp-input mt-2" />
          </div>
          <div>
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.tenants.sector}</label>
            <input required data-testid="tenant-sector" value={form.sector} onChange={e => setForm({ ...form, sector: e.target.value })} className="tkp-input mt-2" />
          </div>
          <div className="flex items-end">
            <button data-testid="tenant-submit" className="tkp-btn-primary">{t.tenants.add}</button>
          </div>
          <div className="md:col-span-3">
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.tenants.description}</label>
            <textarea data-testid="tenant-desc" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="tkp-input mt-2" rows={2} />
          </div>
        </form>
      )}

      <div className="tkp-card p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-[10px] tracking-widest uppercase text-slate-500 font-bold border-b border-slate-200">
              <th className="text-left px-5 py-3">{t.tenants.name}</th>
              <th className="text-left px-5 py-3">{t.tenants.sector}</th>
              <th className="text-left px-5 py-3">{t.tenants.sectorHash}</th>
              <th className="text-left px-5 py-3">{t.tenants.active}</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map(t => (
              <tr key={t.id} className="border-b border-slate-100 hover:bg-slate-50 text-sm" data-testid={`tenant-row-${t.id}`}>
                <td className="px-5 py-3 font-semibold">{t.name}</td>
                <td className="px-5 py-3">{t.sector}</td>
                <td className="px-5 py-3 font-mono text-xs text-slate-500">{t.sector_hash}</td>
                <td className="px-5 py-3">
                  <span className="flex items-center gap-1.5 text-emerald-600 text-xs font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />{t.active ? 'yes' : 'no'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
