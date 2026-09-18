/**
 * SkyGuard AI — Master Top Navigation & Command Bar
 * Professional scientific command bar: text-only navigation, semantic color coding,
 * live transport indicators, active alert counters, and UTC synoptic clock.
 */

import React, { useState, useEffect } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { useAnomalies } from '../hooks/useAnomalies';
import { USE_MOCK_DATA, API_BASE_URL, WS_BASE_URL } from '../api/client';

export const TopCommandBar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { connectionState, lastHeartbeat } = useRealtimeStream();
  const { data: anomalies = [] } = useAnomalies({ limit: 10 });
  const [utcTime, setUtcTime] = useState<string>('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [alertsDropdownOpen, setAlertsDropdownOpen] = useState<boolean>(false);

  // Live UTC Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().slice(11, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setAlertsDropdownOpen(false);
  }, [location.pathname]);

  const navItems = [
    { label: 'Network', path: '/network' },
    { label: 'Live', path: '/live' },
    { label: 'Stations', path: '/stations' },
    { label: 'Anomalies', path: '/anomalies' },
    { label: 'Health', path: '/health' },
    { label: 'Corrections', path: '/corrections' },
    { label: 'History', path: '/history' },
    { label: 'System', path: '/system' },
  ];

  const criticalAnomalies = anomalies.filter((a) => a.severity === 'CRITICAL');
  const alertCount = anomalies.length;

  return (
    <>
      <header className="sticky top-0 z-50 bg-[#0A0E17] border-b border-[#1E293B] select-none">
        <div className="max-w-[1920px] mx-auto px-3 sm:px-4 h-12 flex items-center justify-between gap-2">
          {/* Left: Brand Identity & Operational Status Flag */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => navigate('/network')}
              className="flex items-center gap-2 text-left group focus:outline-none"
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-sm font-bold tracking-wider text-[#F8FAFC]">
                    SKYGUARD
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sky-950/80 text-sky-300 border border-sky-800 font-bold">
                    AI
                  </span>
                </div>
                <span className="text-[9px] font-mono text-[#64748B] tracking-tight uppercase">
                  METEOROLOGICAL OBSERVATION & SENSOR ANOMALY DETECTION
                </span>
              </div>
            </button>

            {/* Mode Banner Pill */}
            {USE_MOCK_DATA ? (
              <span className="hidden xl:inline-flex items-center text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/60 font-medium">
                DEMO HARNESS
              </span>
            ) : (
              <span className="hidden xl:inline-flex items-center text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/60 font-medium">
                FASTAPI PRODUCTION
              </span>
            )}
          </div>

          {/* Center: Desktop Command Navigation Bar (Strictly Text-Only) */}
          <nav className="hidden lg:flex items-center gap-1 h-full">
            {navItems.map((item) => {
              const isActive =
                location.pathname === item.path ||
                (item.path !== '/' && location.pathname.startsWith(`${item.path}/`));

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={`h-9 px-3 flex items-center gap-2 rounded text-xs font-mono transition-colors relative ${
                    isActive
                      ? 'text-sky-300 font-bold bg-[#141E30] border-b-2 border-sky-400'
                      : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#111928]'
                  }`}
                >
                  <span>{item.label}</span>
                  {item.label === 'Anomalies' && alertCount > 0 && (
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                        criticalAnomalies.length > 0
                          ? 'bg-red-950 text-red-300 border border-red-800'
                          : 'bg-amber-950 text-amber-300 border border-amber-800'
                      }`}
                    >
                      {alertCount}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>

          {/* Right: Operational Status, Alerts, Clock, Settings */}
          <div className="flex items-center gap-2 sm:gap-2.5">
            {/* WebSocket / Transport Status */}
            <div
              className={`text-[11px] font-mono px-2.5 py-1 rounded border font-semibold ${
                connectionState === 'CONNECTED'
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                  : connectionState === 'CONNECTING' || connectionState === 'RECONNECTING'
                  ? 'bg-amber-950/40 text-amber-300 border-amber-800/60'
                  : 'bg-red-950/40 text-red-300 border-red-800/60'
              }`}
              title={`WebSocket: ${connectionState}. Heartbeat: ${lastHeartbeat.toISOString()}`}
            >
              <span className="tracking-wide">
                {connectionState === 'CONNECTED' ? 'WS STREAM' : connectionState}
              </span>
            </div>

            {/* Active Alerts Trigger Button */}
            <div className="relative">
              <button
                onClick={() => setAlertsDropdownOpen(!alertsDropdownOpen)}
                className={`text-[11px] font-mono px-2.5 py-1 rounded border font-semibold transition-colors ${
                  criticalAnomalies.length > 0
                    ? 'bg-red-950/60 text-red-300 border-red-800 hover:bg-red-900/60'
                    : alertCount > 0
                    ? 'bg-amber-950/60 text-amber-300 border-amber-800 hover:bg-amber-900/60'
                    : 'bg-[#111827] text-[#94A3B8] border-[#1E293B] hover:text-[#F8FAFC]'
                }`}
                title="Active Anomaly Alerts"
              >
                <span>
                  {alertCount > 0 ? `${alertCount} ALERTS` : '0 ALERTS'}
                </span>
              </button>

              {/* Quick Alerts Dropdown */}
              {alertsDropdownOpen && (
                <div className="absolute right-0 mt-1.5 w-80 bg-[#0F172A] border border-[#1E293B] rounded shadow-2xl p-2.5 z-50 text-xs font-mono space-y-2 animate-fadeIn">
                  <div className="flex items-center justify-between pb-1.5 border-b border-[#1E293B]">
                    <span className="font-bold text-[#F8FAFC]">ACTIVE ALERTS REGISTRY</span>
                    <button
                      onClick={() => {
                        setAlertsDropdownOpen(false);
                        navigate('/anomalies');
                      }}
                      className="text-[10px] text-sky-400 hover:text-sky-300 underline font-sans"
                    >
                      View All
                    </button>
                  </div>
                  {anomalies.length === 0 ? (
                    <div className="py-4 text-center text-[#64748B] text-xs">
                      No active anomalies. Network nominal.
                    </div>
                  ) : (
                    <div className="max-h-60 overflow-y-auto space-y-1 divide-y divide-[#1E293B]/40">
                      {anomalies.slice(0, 5).map((anom) => (
                        <div
                          key={anom.event_id}
                          onClick={() => {
                            setAlertsDropdownOpen(false);
                            navigate(`/anomalies/${anom.event_id}`);
                          }}
                          className="pt-1.5 cursor-pointer hover:bg-[#1E293B]/40 p-1.5 rounded transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sky-300">
                              {anom.station_id}
                            </span>
                            <span
                              className={`text-[9px] px-1 rounded font-bold ${
                                anom.severity === 'CRITICAL'
                                  ? 'bg-red-950 text-red-300 border border-red-800'
                                  : 'bg-amber-950 text-amber-300 border border-amber-800'
                              }`}
                            >
                              {anom.severity}
                            </span>
                          </div>
                          <div className="text-[11px] text-[#94A3B8] font-sans truncate mt-0.5">
                            {anom.explanation_summary}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* UTC Operational Clock */}
            <div className="hidden sm:flex items-center text-xs font-mono font-medium text-[#F8FAFC] bg-[#111827] border border-[#1E293B] px-2.5 py-1 rounded">
              <span>{utcTime || 'UTC'}</span>
            </div>

            {/* Settings Trigger */}
            <button
              onClick={() => setSettingsOpen(!settingsOpen)}
              className="px-2.5 py-1 rounded bg-[#111827] hover:bg-[#1E293B] border border-[#1E293B] text-[#94A3B8] hover:text-[#F8FAFC] transition-colors text-xs font-mono font-semibold"
              title="Platform Settings & Endpoints"
            >
              CONFIG
            </button>

            {/* Mobile Menu Hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden px-2.5 py-1 rounded bg-[#111827] hover:bg-[#1E293B] border border-[#1E293B] text-[#94A3B8] hover:text-[#F8FAFC] transition-colors text-xs font-mono font-semibold"
              title="Toggle Menu"
            >
              {mobileMenuOpen ? 'CLOSE' : 'MENU'}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden bg-[#0A0E17] border-t border-[#1E293B] px-3 py-2 space-y-1 font-mono text-xs">
            <div className="text-[10px] text-[#64748B] uppercase px-2 py-1 font-bold">
              COMMAND SECTIONS
            </div>
            {navItems.map((item) => {
              const isActive =
                location.pathname === item.path ||
                (item.path !== '/' && location.pathname.startsWith(`${item.path}/`));

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center justify-between px-3 py-2 rounded ${
                    isActive
                      ? 'bg-[#141E30] text-sky-300 font-bold border-l-2 border-sky-400'
                      : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#111928]'
                  }`}
                >
                  <span className="font-bold">{item.label}</span>
                  {item.label === 'Anomalies' && alertCount > 0 && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 font-bold">
                      {alertCount}
                    </span>
                  )}
                </NavLink>
              );
            })}
            <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[11px] text-[#64748B] px-2 font-mono">
              <span>TIME: {utcTime}</span>
              <span>TRANSPORT: {connectionState}</span>
            </div>
          </div>
        )}
      </header>

      {/* Settings Modal Drawer */}
      {settingsOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#0F172A] border border-[#1E293B] rounded w-full max-w-lg p-4 font-mono text-xs space-y-3.5 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
              <span className="font-bold text-[#F8FAFC] text-sm tracking-wide">
                OPERATIONAL PARAMETERS & INTEGRATION CONFIG
              </span>
              <button
                onClick={() => setSettingsOpen(false)}
                className="text-[#94A3B8] hover:text-white px-2 py-0.5 text-xs font-bold"
              >
                CLOSE
              </button>
            </div>

            <div className="space-y-2.5">
              <div className="bg-[#0A0E17] border border-[#1E293B] p-2.5 rounded space-y-1">
                <div className="text-[10px] text-[#64748B] uppercase font-bold">
                  ACTIVE EXECUTION MODE
                </div>
                <div className="text-sm font-bold text-[#F8FAFC]">
                  {USE_MOCK_DATA
                    ? 'DEMO / MOCK DATA HARNESS'
                    : 'PRODUCTION FASTAPI BACKEND'}
                </div>
                <p className="text-[11px] text-[#94A3B8] font-sans">
                  {USE_MOCK_DATA
                    ? 'Synthetic weather vectors simulating realistic extreme events, sensor spikes, and spatial gradients without live hardware.'
                    : 'Directly communicating with FastAPI backend endpoints per openapi.json contract.'}
                </p>
              </div>

              <div className="bg-[#0A0E17] border border-[#1E293B] p-2.5 rounded space-y-1">
                <div className="text-[10px] text-[#64748B] uppercase font-bold">
                  AUTHORITATIVE REST BASE URL
                </div>
                <div className="text-sky-300 font-bold break-all">{API_BASE_URL}</div>
              </div>

              <div className="bg-[#0A0E17] border border-[#1E293B] p-2.5 rounded space-y-1">
                <div className="text-[10px] text-[#64748B] uppercase font-bold">
                  REAL-TIME WEBSOCKET STREAM
                </div>
                <div className="text-emerald-300 font-bold break-all">{WS_BASE_URL}</div>
              </div>

              <div className="bg-[#0A0E17] border border-[#1E293B] p-2.5 rounded space-y-1">
                <div className="text-[10px] text-[#64748B] uppercase font-bold">
                  ENVIRONMENT CONFIGURATION
                </div>
                <div className="text-[11px] text-[#94A3B8] font-sans">
                  To connect to your local backend, edit <code className="text-sky-300">.env</code>:
                  <pre className="mt-1 bg-[#141E30] p-1.5 rounded text-[10px] text-emerald-300 overflow-x-auto font-mono">
                    {`VITE_USE_MOCK_DATA=false\nVITE_API_BASE_URL=http://localhost:8000/api/v1\nVITE_WS_URL=ws://localhost:8000/ws/stream`}
                  </pre>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-[#1E293B]">
              <button
                onClick={() => setSettingsOpen(false)}
                className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded font-bold text-xs transition-colors font-mono"
              >
                CLOSE CONFIG
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
