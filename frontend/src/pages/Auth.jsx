import React, { useContext, useState } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';

const LogoMark = () => (
  <svg viewBox="0 0 64 64" width="56" height="56" aria-hidden>
    <rect width="64" height="64" rx="18" fill="#0A0A0A" />
    <g fill="none" stroke="white" strokeWidth="3">
      <circle cx="32" cy="32" r="22" />
      <circle cx="32" cy="32" r="10" />
    </g>
    <path d="M32 28v8M28 32h8" stroke="white" strokeWidth="3" strokeLinecap="square" />
  </svg>
);

export default function Auth() {
  const { login, t, locale, setLocale } = useContext(AppCtx);
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('admin@talktoplus.io');
  const [password, setPassword] = useState('Admin!2026');
  const [fullName, setFullName] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    try {
      if (mode === 'login') {
        const r = await http.post('/auth/login', { email, password });
        login(r.data.access_token, r.data.user);
      } else {
        const r = await http.post('/auth/register', { email, password, full_name: fullName });
        login(r.data.access_token, r.data.user);
      }
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Error');
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row" data-testid="auth-page">
      {/* Left side - brand */}
      <div className="md:w-1/2 bg-ink text-white p-10 md:p-16 flex flex-col justify-between relative overflow-hidden tkp-grain">
        <div className="relative z-10 flex items-center gap-4">
          <LogoMark />
          <div>
            <div className="font-heading text-2xl font-black tracking-tighter">{t.appName} <span className="text-slate-500">/ {t.appSub}</span></div>
            <div className="text-[11px] text-slate-400 tracking-[0.3em] mt-1">EXECUTION RISK VALIDATION</div>
          </div>
        </div>

        <div className="relative z-10">
          <h1 className="font-heading text-4xl md:text-6xl font-black tracking-tighter leading-[0.95]">
            From Diagnostic<br />to Prescriptive.
          </h1>
          <p className="mt-6 text-slate-300 text-base max-w-md leading-relaxed">
            Sovereign Edge for Enterprise Intelligence. Closed-loop swarm analytics — your data never leaves the tenant.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-6 max-w-md">
            {[
              { k: '70%', v: 'of strategies fail at execution' },
              { k: '0', v: 'raw data leaves tenant' },
              { k: '1.3', v: 'version production' },
            ].map((m, i) => (
              <div key={i}>
                <div className="font-heading text-3xl font-black tracking-tighter">{m.k}</div>
                <div className="text-[10px] tracking-widest uppercase text-slate-400 mt-1">{m.v}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 text-[11px] text-slate-500 tracking-wide">
          © 2026 TALK TO+. Proprietary. — Four-Eyes Principle enforced.
        </div>
      </div>

      {/* Right side - form */}
      <div className="md:w-1/2 flex items-center justify-center p-8 md:p-16 bg-white">
        <div className="w-full max-w-sm">
          <div className="flex justify-end mb-8">
            <button
              data-testid="auth-lang-toggle"
              onClick={() => setLocale(locale === 'fi' ? 'en' : 'fi')}
              className="text-[11px] font-bold tracking-widest text-slate-500 hover:text-ink"
            >
              {locale === 'fi' ? 'FI · EN' : 'EN · FI'}
            </button>
          </div>

          <div className="flex border-b border-slate-200 mb-8">
            <button
              data-testid="tab-login"
              onClick={() => setMode('login')}
              className={`flex-1 py-3 text-sm font-bold tracking-widest uppercase ${mode === 'login' ? 'border-b-2 border-ink text-ink' : 'text-slate-400'}`}>
              {t.auth.login}
            </button>
            <button
              data-testid="tab-register"
              onClick={() => setMode('register')}
              className={`flex-1 py-3 text-sm font-bold tracking-widest uppercase ${mode === 'register' ? 'border-b-2 border-ink text-ink' : 'text-slate-400'}`}>
              {t.auth.register}
            </button>
          </div>

          <form onSubmit={submit} className="space-y-5" data-testid="auth-form">
            {mode === 'register' && (
              <div>
                <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.auth.fullName}</label>
                <input data-testid="input-fullname" required value={fullName} onChange={e => setFullName(e.target.value)} className="tkp-input mt-2" />
              </div>
            )}
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.auth.email}</label>
              <input data-testid="input-email" required type="email" value={email} onChange={e => setEmail(e.target.value)} className="tkp-input mt-2" />
            </div>
            <div>
              <label className="text-[11px] tracking-widest uppercase text-slate-500 font-bold">{t.auth.password}</label>
              <input data-testid="input-password" required type="password" value={password} onChange={e => setPassword(e.target.value)} className="tkp-input mt-2" />
            </div>
            {err && <div className="text-xs text-red-600 font-medium">{err}</div>}
            <button data-testid="submit-auth" disabled={busy} className="tkp-btn-primary w-full mt-2">
              {busy ? '…' : (mode === 'login' ? t.auth.signIn : t.auth.signUp)}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-200 text-[11px] text-slate-500 font-mono">
            {t.auth.demoHint}
          </div>
        </div>
      </div>
    </div>
  );
}
