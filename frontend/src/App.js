import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { http } from './api';
import { useT } from './i18n';
import Layout from './components/Layout';
import Auth from './pages/Auth';
import Boardroom from './pages/Boardroom';
import SignalsRadar from './pages/SignalsRadar';
import DecisionHub from './pages/DecisionHub';
import GlobalIntel from './pages/GlobalIntel';
import ActionCards from './pages/ActionCards';
import StrategyRAG from './pages/StrategyRAG';
import Tenants from './pages/Tenants';
import SystemHealth from './pages/SystemHealth';
import Notifications from './pages/Notifications';

export const AppCtx = React.createContext(null);

export default function App() {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('tkp_user');
    return raw ? JSON.parse(raw) : null;
  });
  const [locale, setLocale] = useState(() => localStorage.getItem('tkp_locale') || 'fi');
  const t = useT(locale);

  useEffect(() => { localStorage.setItem('tkp_locale', locale); }, [locale]);

  // refresh user
  useEffect(() => {
    if (!user) return;
    http.get('/auth/me').then(r => {
      localStorage.setItem('tkp_user', JSON.stringify(r.data));
      setUser(r.data);
    }).catch(() => {});
  }, []); // run once on mount

  const login = (token, u) => {
    localStorage.setItem('tkp_token', token);
    localStorage.setItem('tkp_user', JSON.stringify(u));
    setUser(u);
  };
  const logout = () => {
    localStorage.removeItem('tkp_token');
    localStorage.removeItem('tkp_user');
    setUser(null);
  };

  const ctx = { user, login, logout, locale, setLocale, t };

  return (
    <AppCtx.Provider value={ctx}>
      <BrowserRouter>
        <Routes>
          <Route path="/auth" element={user ? <Navigate to="/" /> : <Auth />} />
          <Route element={user ? <Layout /> : <Navigate to="/auth" />}>
            <Route path="/" element={<Boardroom />} />
            <Route path="/signals" element={<SignalsRadar />} />
            <Route path="/decision" element={<DecisionHub />} />
            <Route path="/global" element={<GlobalIntel />} />
            <Route path="/actions" element={<ActionCards />} />
            <Route path="/rag" element={<StrategyRAG />} />
            <Route path="/tenants" element={<Tenants />} />
            <Route path="/system" element={<SystemHealth />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppCtx.Provider>
  );
}
