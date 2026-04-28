import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { Plus, Trash, PaperPlaneTilt, SlackLogo, MicrosoftTeamsLogo } from '@phosphor-icons/react';

export default function Notifications() {
  const { t } = useContext(AppCtx);
  const [channels, setChannels] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ type: 'slack', webhook_url: '', min_severity: 'HIGH', label: '' });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = () => http.get('/notifications').then(r => setChannels(r.data));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setMsg(null);
    try {
      await http.post('/notifications', form);
      setForm({ type: 'slack', webhook_url: '', min_severity: 'HIGH', label: '' });
      setShow(false);
      await load();
    } catch (err) {
      setMsg({ kind: 'err', text: err?.response?.data?.detail || 'Error' });
    } finally { setBusy(false); }
  };

  const test = async (id) => {
    setMsg(null);
    try {
      await http.post(`/notifications/${id}/test`);
      setMsg({ kind: 'ok', text: 'Test alert sent. Check your channel.' });
    } catch (err) {
      setMsg({ kind: 'err', text: err?.response?.data?.detail || 'Test failed' });
    }
  };

  const del = async (id) => { await http.delete(`/notifications/${id}`); load(); };

  return (
    <div data-testid="notifications-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">Notifications</h1>
          <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">Slack / Teams Oracle alerts</div>
        </div>
        <button onClick={() => setShow(!show)} className="tkp-btn-primary flex items-center gap-2" data-testid="new-channel-btn">
          <Plus size={14} weight="bold" />Add channel
        </button>
      </div>

      {msg && (
        <div className={`mb-4 p-3 rounded-sm text-sm ${msg.kind === 'ok' ? 'sev-LOW' : 'sev-CRITICAL'} border`}>
          {msg.text}
        </div>
      )}

      {show && (
        <form onSubmit={submit} className="tkp-card p-6 mb-6 space-y-4" data-testid="new-channel-form">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">Type</label>
              <select data-testid="ch-type" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} className="tkp-input mt-2">
                <option value="slack">Slack</option>
                <option value="teams">Microsoft Teams</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">Min severity</label>
              <select data-testid="ch-sev" value={form.min_severity} onChange={e => setForm({ ...form, min_severity: e.target.value })} className="tkp-input mt-2">
                <option>LOW</option><option>MODERATE</option><option>HIGH</option><option>CRITICAL</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">Label</label>
              <input data-testid="ch-label" value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} className="tkp-input mt-2" placeholder="e.g. #execution-risks" />
            </div>
          </div>
          <div>
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">Webhook URL</label>
            <input data-testid="ch-url" required type="url" value={form.webhook_url} onChange={e => setForm({ ...form, webhook_url: e.target.value })} className="tkp-input mt-2 font-mono text-xs" placeholder="https://hooks.slack.com/services/..." />
            <div className="text-[10px] text-slate-500 mt-1 font-mono">
              Slack: api.slack.com/apps → Incoming Webhooks · Teams: channel → Connectors → Incoming Webhook
            </div>
          </div>
          <button data-testid="ch-submit" disabled={busy} className="tkp-btn-primary">
            {busy ? '…' : 'Add channel'}
          </button>
        </form>
      )}

      <div className="tkp-card p-0 overflow-hidden">
        {channels.length === 0 && <div className="p-6 text-sm text-slate-400">No channels configured. Add one above.</div>}
        {channels.map(c => (
          <div key={c.id} className="p-5 border-b border-slate-100 last:border-none flex items-center gap-4" data-testid={`ch-${c.id}`}>
            <div className="w-10 h-10 rounded-sm border border-slate-200 flex items-center justify-center">
              {c.type === 'slack' ? <SlackLogo size={18} weight="duotone" /> : <MicrosoftTeamsLogo size={18} weight="duotone" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{c.label || c.type}</div>
              <div className="text-[10px] tracking-widest uppercase text-slate-500 font-mono mt-0.5">
                {c.type} · min severity: {c.min_severity}
              </div>
              <div className="text-xs text-slate-400 font-mono truncate mt-1">{c.webhook_url}</div>
            </div>
            <button onClick={() => test(c.id)} className="px-3 py-1.5 text-xs font-bold tracking-widest uppercase border border-slate-200 rounded-sm hover:border-ink flex items-center gap-1" data-testid={`ch-test-${c.id}`}>
              <PaperPlaneTilt size={12} />Test
            </button>
            <button onClick={() => del(c.id)} className="text-slate-400 hover:text-red-600" data-testid={`ch-del-${c.id}`}>
              <Trash size={16} />
            </button>
          </div>
        ))}
      </div>

      <div className="mt-6 text-[10px] text-slate-500 font-mono">
        Dispatcher status: {window?.location?.hostname?.includes('localhost') ? 'enable via ENABLE_DISPATCHER=true' : 'controlled by deployment'}
      </div>
    </div>
  );
}
