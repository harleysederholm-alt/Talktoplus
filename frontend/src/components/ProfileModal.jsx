import React, { useContext, useState } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { X, Check } from '@phosphor-icons/react';
import { toast } from 'sonner';

const ROLE_BADGES = {
  facilitator: { label: 'Facilitator', cls: 'bg-teal-100 text-teal-800 border-teal-300' },
  executive: { label: 'Executive', cls: 'bg-purple-100 text-purple-800 border-purple-300' },
  super_admin: { label: 'Admin', cls: 'bg-amber-100 text-amber-800 border-amber-300' },
  admin: { label: 'Admin', cls: 'bg-amber-100 text-amber-800 border-amber-300' },
  viewer: { label: 'Viewer', cls: 'bg-slate-100 text-slate-700 border-slate-300' },
};

export default function ProfileModal({ open, onClose }) {
  const { user, t, locale, setUser } = useContext(AppCtx);
  const [name, setName] = useState(user?.full_name || '');
  const [notif, setNotif] = useState(user?.notification_preferences || { email: true, slack: false });
  const [busy, setBusy] = useState(false);

  if (!open || !user) return null;

  const switchRole = async (role) => {
    setBusy(true);
    try {
      const r = await http.post('/auth/role', { role });
      setUser(r.data);
      toast.success(t.profile.switchedTo.replace('{role}', t.profile[role] || role));
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error');
    } finally { setBusy(false); }
  };

  const save = async () => {
    setBusy(true);
    try {
      const r = await http.patch('/auth/profile', { full_name: name, locale, notification_preferences: notif });
      setUser(r.data);
      toast.success(t.profile.saved);
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error');
    } finally { setBusy(false); }
  };

  const badge = ROLE_BADGES[user.role] || ROLE_BADGES.viewer;

  return (
    <div
      data-testid="profile-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-sm w-full max-w-md mx-4 shadow-2xl border border-slate-200 animate-fade-up">
        <div className="flex items-center justify-between p-5 border-b border-slate-200">
          <div>
            <div className="font-heading text-lg font-bold tracking-tight">{t.profile.title}</div>
          </div>
          <button data-testid="profile-close" onClick={onClose} className="text-slate-400 hover:text-ink"><X size={18} /></button>
        </div>

        <div className="p-5 space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-ink text-white flex items-center justify-center text-sm font-bold tracking-wider">
              {(user.full_name || '').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1">
              <div className="font-semibold">{user.full_name}</div>
              <div className="text-[11px] text-slate-500 font-mono">{user.email}</div>
            </div>
            <span className={`text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border rounded-sm ${badge.cls}`}>{badge.label}</span>
          </div>

          <div>
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">Name</label>
            <input data-testid="profile-name" value={name} onChange={e => setName(e.target.value)} className="tkp-input mt-2" />
          </div>

          <div>
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.profile.organization}</label>
            <input value="Metso Outotec" disabled className="tkp-input mt-2 bg-slate-50 text-slate-500" />
          </div>

          <div>
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.profile.switchRole}</label>
            <div className="flex gap-2 mt-2">
              {[
                { k: 'facilitator', l: t.profile.facilitator },
                { k: 'executive', l: t.profile.executive },
                { k: 'super_admin', l: t.profile.admin },
              ].map(r => (
                <button
                  key={r.k}
                  data-testid={`role-${r.k}`}
                  disabled={busy}
                  onClick={() => switchRole(r.k)}
                  className={`flex-1 px-3 py-2 text-[11px] font-bold tracking-widest uppercase rounded-sm border transition-colors ${
                    user.role === r.k ? 'bg-ink text-white border-ink' : 'bg-white text-slate-600 border-slate-200 hover:border-ink'
                  }`}
                >
                  {r.l}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.profile.notifications}</label>
            <div className="mt-2 space-y-2">
              {[
                { k: 'email', l: 'Email' },
                { k: 'slack', l: 'Slack' },
                { k: 'oracle_alerts', l: 'Oracle alerts (HIGH+)' },
              ].map(o => (
                <label key={o.k} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    data-testid={`pref-${o.k}`}
                    type="checkbox"
                    checked={!!notif[o.k]}
                    onChange={e => setNotif({ ...notif, [o.k]: e.target.checked })}
                    className="w-4 h-4 accent-ink"
                  />
                  {o.l}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 p-5 border-t border-slate-200">
          <button onClick={onClose} className="px-4 py-2 text-xs font-bold tracking-widest uppercase border border-slate-200 rounded-sm hover:border-ink">{t.cancel}</button>
          <button data-testid="profile-save" onClick={save} disabled={busy} className="tkp-btn-primary flex items-center gap-2">
            <Check size={14} weight="bold" />{busy ? '…' : t.save}
          </button>
        </div>
      </div>
    </div>
  );
}
