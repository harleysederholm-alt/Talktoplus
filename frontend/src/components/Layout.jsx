import React, { useContext, useEffect, useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { AppCtx } from '../App';
import { http } from '../api';
import {
  Television, Broadcast, ShieldCheck, UsersThree, Cards,
  SquaresFour, Buildings, Heartbeat, MagnifyingGlass,
  Bell, SignOut, Globe, BellRinging
} from '@phosphor-icons/react';

const LogoMark = () => (
  <svg viewBox="0 0 64 64" width="36" height="36" aria-hidden>
    <rect width="64" height="64" rx="18" fill="#0A0A0A" />
    <g fill="none" stroke="white" strokeWidth="3">
      <circle cx="32" cy="32" r="22" />
      <circle cx="32" cy="32" r="10" />
    </g>
    <path d="M32 28v8M28 32h8" stroke="white" strokeWidth="3" strokeLinecap="square" />
  </svg>
);

const NavItem = ({ to, icon: Icon, label, sub }) => (
  <NavLink
    to={to}
    data-testid={`nav-${to.replace('/', '') || 'boardroom'}`}
    className={({ isActive }) =>
      `flex items-start gap-3 px-4 py-3 rounded-sm transition-colors ${
        isActive ? 'bg-white/10 text-white' : 'text-slate-300 hover:text-white hover:bg-white/5'
      }`
    }
  >
    <Icon size={20} weight="duotone" className="mt-0.5 shrink-0" />
    <div className="min-w-0">
      <div className="text-sm font-semibold tracking-tight">{label}</div>
      <div className="text-[11px] text-slate-400 tracking-wide">{sub}</div>
    </div>
  </NavLink>
);

export default function Layout() {
  const { user, logout, locale, setLocale, t } = useContext(AppCtx);
  const location = useLocation();
  const [gri, setGri] = useState({ value: 1.0, trend: 'stable', active: 0, total: 0 });
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const fetchGri = () => http.get('/analytics/global-risk-index').then(r => setGri(r.data)).catch(() => {});
    fetchGri();
    const id = setInterval(() => { setNow(new Date()); fetchGri(); }, 30000);
    return () => clearInterval(id);
  }, [location.pathname]);

  const trendLabel = gri.trend === 'rising' ? t.boardroom.rising :
                     gri.trend === 'falling' ? t.boardroom.falling : t.boardroom.stable;
  const trendColor = gri.trend === 'rising' ? 'text-red-500' :
                     gri.trend === 'falling' ? 'text-emerald-500' : 'text-emerald-500';

  return (
    <div className="min-h-screen flex bg-canvas">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 bg-ink text-white flex flex-col tkp-sidebar" data-testid="sidebar">
        <div className="px-5 py-6 border-b border-slate-800 flex items-center gap-3">
          <LogoMark />
          <div>
            <div className="font-heading text-xl font-black tracking-tighter leading-none">{t.appName}</div>
            <div className="text-[10px] text-slate-400 tracking-[0.25em] mt-1">{t.appSub}</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <NavItem to="/" icon={Television} label={t.nav.boardroom} sub={t.nav.boardroomSub} />
          <NavItem to="/signals" icon={Broadcast} label={t.nav.signals} sub={t.nav.signalsSub} />
          <NavItem to="/decision" icon={ShieldCheck} label={t.nav.decision} sub={t.nav.decisionSub} />
          <NavItem to="/global" icon={UsersThree} label={t.nav.global} sub={t.nav.globalSub} />
          <NavItem to="/actions" icon={Cards} label={t.nav.actions} sub={t.nav.actionsSub} />
          <NavItem to="/rag" icon={SquaresFour} label={t.nav.rag} sub={t.nav.ragSub} />
          <NavItem to="/tenants" icon={Buildings} label={t.nav.tenants} sub={t.nav.tenantsSub} />
          <NavItem to="/system" icon={Heartbeat} label={t.nav.system} sub={t.nav.systemSub} />
          <NavItem to="/notifications" icon={BellRinging} label="Notifications" sub="Slack / Teams" />
        </nav>

        {/* Global Risk Index widget */}
        <div className="mx-3 mb-3 p-4 rounded-sm bg-white/5 border border-slate-800" data-testid="gri-widget">
          <div className="text-[10px] tracking-[0.2em] text-slate-400 uppercase">Global Risk Index</div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="font-heading text-4xl font-black tracking-tighter">{gri.value}</span>
            <span className={`text-[11px] font-bold tracking-widest ${trendColor}`}>{trendLabel}</span>
          </div>
          <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-400 font-mono">
            <span>↑ {gri.active} active</span>
            <span>{gri.total} total</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 font-mono">
            Updated {now.toTimeString().slice(0, 8)}
          </div>
        </div>

        <div className="px-5 py-3 border-t border-slate-800 text-[10px] text-slate-500">
          TALK TO+ BDaaS<br />© 2026 All Rights Reserved
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <header className="h-16 bg-canvas border-b border-slate-200 flex items-center px-8 gap-4 sticky top-0 z-20" data-testid="topbar">
          <div className="flex-1 relative max-w-xl">
            <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              data-testid="global-search"
              className="w-full pl-9 pr-14 py-2 bg-white border border-slate-200 rounded-sm text-sm focus:outline-none focus:border-ink"
              placeholder={t.search}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-mono px-1.5 py-0.5 border border-slate-200 rounded">⌘K</span>
          </div>

          <button
            data-testid="lang-toggle"
            onClick={() => setLocale(locale === 'fi' ? 'en' : 'fi')}
            className="flex items-center gap-1.5 text-xs font-bold tracking-widest text-slate-600 hover:text-ink px-2 py-1 border border-slate-200 rounded-sm"
          >
            <Globe size={14} />
            {locale === 'fi' ? 'FI / EN' : 'EN / FI'}
          </button>

          <button className="relative w-9 h-9 rounded-full border border-slate-200 flex items-center justify-center text-slate-600 hover:text-ink" data-testid="notifications">
            <Bell size={16} />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
          </button>

          <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
            <div className="w-9 h-9 rounded-full bg-ink text-white flex items-center justify-center text-xs font-bold tracking-wider" data-testid="user-avatar">
              {user?.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'AN'}
            </div>
            <div className="text-right leading-tight">
              <div className="text-sm font-semibold">{user?.full_name}</div>
              <div className="text-[10px] uppercase tracking-widest text-slate-500">{user?.role?.replace('_', ' ')}</div>
            </div>
            <button onClick={logout} className="text-slate-400 hover:text-ink" title={t.signOut} data-testid="logout-btn">
              <SignOut size={18} />
            </button>
          </div>
        </header>

        {/* Status strip */}
        <div className="px-8 pt-6 flex items-center justify-end gap-6 text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /><span className="font-semibold text-slate-700">{t.liveLabel}</span></div>
          <div className="flex items-center gap-1.5"><ShieldCheck size={14} /><span>{t.fourEyes}</span></div>
          <div className="font-mono">{t.version}</div>
        </div>

        <div className="flex-1 px-8 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
