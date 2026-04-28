import React, { useContext, useEffect, useState } from 'react';
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { AppCtx } from '../App';
import { http } from '../api';
import {
  Television, Broadcast, ShieldCheck, UsersThree, Cards,
  SquaresFour, Buildings, Heartbeat, MagnifyingGlass,
  Bell, SignOut, Globe, BellRinging, X
} from '@phosphor-icons/react';
import ProfileModal from './ProfileModal';

const ROLE_BADGES = {
  facilitator: { label: 'Facilitator', cls: 'bg-teal-500/20 text-teal-300 border-teal-400/40' },
  executive: { label: 'Executive', cls: 'bg-purple-500/20 text-purple-300 border-purple-400/40' },
  super_admin: { label: 'Admin', cls: 'bg-amber-500/20 text-amber-300 border-amber-400/40' },
  admin: { label: 'Admin', cls: 'bg-amber-500/20 text-amber-300 border-amber-400/40' },
  viewer: { label: 'Viewer', cls: 'bg-slate-500/20 text-slate-300 border-slate-400/40' },
};

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

// Visibility per role — same nav for all but with role-aware badges; certain pages hidden for non-admin
const NAV_VISIBILITY = {
  '/': ['facilitator', 'executive', 'super_admin', 'admin', 'viewer'],
  '/signals': ['facilitator', 'super_admin', 'admin'],
  '/decision': ['facilitator', 'super_admin', 'admin'],
  '/global': ['executive', 'super_admin', 'admin'],
  '/actions': ['facilitator', 'executive', 'super_admin', 'admin'],
  '/rag': ['facilitator', 'super_admin', 'admin'],
  '/tenants': ['super_admin', 'admin'],
  '/system': ['super_admin', 'admin'],
  '/notifications': ['facilitator', 'executive', 'super_admin', 'admin'],
};

export default function Layout() {
  const { user, logout, locale, setLocale, t, timeRange, setTimeRange, search, setSearch } = useContext(AppCtx);
  const location = useLocation();
  const navigate = useNavigate();
  const [gri, setGri] = useState({ value: 1.0, trend: 'stable', active: 0, total: 0 });
  const [now, setNow] = useState(new Date());
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    const fetchGri = () => http.get('/analytics/global-risk-index').then(r => setGri(r.data)).catch(() => {});
    fetchGri();
    const id = setInterval(() => { setNow(new Date()); fetchGri(); }, 30000);
    return () => clearInterval(id);
  }, [location.pathname]);

  // If user lands on a route their role can't see, redirect to boardroom
  useEffect(() => {
    const allowed = NAV_VISIBILITY[location.pathname] || ['facilitator', 'executive', 'super_admin', 'admin', 'viewer'];
    if (user && !allowed.includes(user.role)) navigate('/');
  }, [location.pathname, user?.role]); // eslint-disable-line

  const trendLabel = gri.trend === 'rising' ? t.boardroom.rising :
                     gri.trend === 'falling' ? t.boardroom.falling : t.boardroom.stable;
  const trendColor = gri.trend === 'rising' ? 'text-red-500' :
                     gri.trend === 'falling' ? 'text-emerald-500' : 'text-emerald-500';

  const can = (path) => (NAV_VISIBILITY[path] || []).includes(user?.role);
  const badge = ROLE_BADGES[user?.role] || ROLE_BADGES.viewer;

  return (
    <div className="min-h-screen flex bg-canvas">
      {/* Demo banner */}
      <div className="fixed top-0 left-0 right-0 h-6 bg-slate-900 text-slate-300 text-[10px] tracking-[0.3em] uppercase flex items-center justify-center z-40 font-mono">
        {t.demoBanner}
      </div>

      {/* Sidebar */}
      <aside className="w-64 shrink-0 bg-ink text-white flex flex-col tkp-sidebar pt-6" data-testid="sidebar">
        <div className="px-5 py-6 border-b border-slate-800 flex items-center gap-3">
          <LogoMark />
          <div>
            <div className="font-heading text-xl font-black tracking-tighter leading-none">{t.appName}</div>
            <div className="text-[10px] text-slate-400 tracking-[0.25em] mt-1">{t.appSub}</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {can('/') && <NavItem to="/" icon={Television} label={t.nav.boardroom} sub={t.nav.boardroomSub} />}
          {can('/signals') && <NavItem to="/signals" icon={Broadcast} label={t.nav.signals} sub={t.nav.signalsSub} />}
          {can('/decision') && <NavItem to="/decision" icon={ShieldCheck} label={t.nav.decision} sub={t.nav.decisionSub} />}
          {can('/global') && <NavItem to="/global" icon={UsersThree} label={t.nav.global} sub={t.nav.globalSub} />}
          {can('/actions') && <NavItem to="/actions" icon={Cards} label={t.nav.actions} sub={t.nav.actionsSub} />}
          {can('/rag') && <NavItem to="/rag" icon={SquaresFour} label={t.nav.rag} sub={t.nav.ragSub} />}
          {can('/tenants') && <NavItem to="/tenants" icon={Buildings} label={t.nav.tenants} sub={t.nav.tenantsSub} />}
          {can('/system') && <NavItem to="/system" icon={Heartbeat} label={t.nav.system} sub={t.nav.systemSub} />}
          {can('/notifications') && <NavItem to="/notifications" icon={BellRinging} label={t.nav.notifications} sub={t.nav.notificationsSub} />}
        </nav>

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
          <div className="mt-1 text-[10px] text-slate-500 font-mono">Updated {now.toTimeString().slice(0, 8)}</div>
        </div>

        <div className="px-5 py-3 border-t border-slate-800 text-[10px] text-slate-500">
          TALK TO+ BDaaS<br />© 2026 All Rights Reserved
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 flex flex-col pt-6">
        <header className="h-16 bg-canvas border-b border-slate-200 flex items-center px-8 gap-4 sticky top-6 z-20" data-testid="topbar">
          <div className="flex-1 relative max-w-xl">
            <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              data-testid="global-search"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-14 py-2 bg-white border border-slate-200 rounded-sm text-sm focus:outline-none focus:border-ink"
              placeholder={t.search}
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-ink">
                <X size={14} />
              </button>
            )}
          </div>

          {/* Time range filter now lives inside Boardroom trend card.
              Topbar kept clean for search + lang + profile. */}

          <button
            data-testid="lang-toggle"
            onClick={() => setLocale(locale === 'fi' ? 'en' : 'fi')}
            className="flex items-center gap-1.5 text-xs font-bold tracking-widest text-slate-600 hover:text-ink px-2 py-1.5 border border-slate-200 rounded-sm bg-white"
          >
            <Globe size={14} />
            {locale === 'fi' ? 'FI · EN' : 'EN · FI'}
          </button>

          <button className="relative w-9 h-9 rounded-full border border-slate-200 bg-white flex items-center justify-center text-slate-600 hover:text-ink" data-testid="notifications-btn">
            <Bell size={16} />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
          </button>

          <button
            data-testid="user-avatar"
            onClick={() => setProfileOpen(true)}
            className="flex items-center gap-3 pl-3 border-l border-slate-200 hover:opacity-80"
          >
            <div className="w-9 h-9 rounded-full bg-ink text-white flex items-center justify-center text-xs font-bold tracking-wider">
              {user?.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'AN'}
            </div>
            <div className="text-right leading-tight">
              <div className="text-sm font-semibold flex items-center gap-1.5">
                {user?.full_name}
                <span className={`text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 border rounded-sm ${badge.cls.replace('text-', 'text-').replace('/20', '').replace('/40', '/60')}`} style={{ background: badge.cls.includes('teal') ? '#CCFBF1' : badge.cls.includes('purple') ? '#F3E8FF' : badge.cls.includes('amber') ? '#FEF3C7' : '#F1F5F9', color: badge.cls.includes('teal') ? '#0F766E' : badge.cls.includes('purple') ? '#7E22CE' : badge.cls.includes('amber') ? '#B45309' : '#475569' }}>
                  {badge.label}
                </span>
              </div>
              <div className="text-[10px] uppercase tracking-widest text-slate-500">{user?.email}</div>
            </div>
          </button>
          <button onClick={logout} className="text-slate-400 hover:text-ink ml-2" title={t.signOut} data-testid="logout-btn">
            <SignOut size={18} />
          </button>
        </header>

        <div className="px-8 pt-6 flex items-center justify-end gap-6 text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /><span className="font-semibold text-slate-700">{t.liveLabel}</span></div>
          <div className="flex items-center gap-1.5"><ShieldCheck size={14} /><span>{t.fourEyes}</span></div>
          <div className="font-mono">{t.version}</div>
        </div>

        <div className="flex-1 px-8 py-6">
          <Outlet />
        </div>
      </main>

      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </div>
  );
}
