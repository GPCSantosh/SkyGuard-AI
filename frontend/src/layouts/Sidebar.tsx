/**
 * SkyGuard AI — Operations Navigation Sidebar
 * 200px fixed width sidebar with navigation links and station quick-switcher.
 */

import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useStations } from '../hooks/useStations';

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: stations = [] } = useStations();

  const navItems = [
    { path: '/network', label: 'Network Overview', glyph: '☷' },
    { path: '/live', label: 'Live Monitoring', glyph: '◉' },
    { path: '/health', label: 'Sensor Health', glyph: '✚' },
    { path: '/corrections', label: 'Advisory Review', glyph: '⚖' },
    { path: '/history', label: 'Historical Analysis', glyph: '◷' },
    { path: '/system', label: 'System Observability', glyph: '⚙' },
  ];

  return (
    <aside className="w-52 bg-[#0E1420] border-r border-[#2D3748] flex flex-col h-[calc(100vh-40px)] select-none shrink-0">
      {/* Primary Navigation Links */}
      <nav className="p-2 space-y-1">
        <div className="px-2 py-1 text-[10px] font-mono text-[#64748B] uppercase tracking-wider">
          OPERATIONAL VIEWS
        </div>
        {navItems.map((item) => {
          const isActive =
            location.pathname === item.path ||
            (item.path === '/network' && location.pathname === '/');

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs font-mono transition-colors ${
                isActive
                  ? 'bg-[#1A2234] text-sky-400 font-semibold border-l-2 border-sky-400 pl-2'
                  : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#161F30]'
              }`}
            >
              <span className="text-xs text-[#64748B]">{item.glyph}</span>
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Station Quick-Switcher */}
      <div className="mt-4 flex-1 flex flex-col min-h-0 border-t border-[#2D3748] pt-2">
        <div className="px-3 py-1 flex items-center justify-between text-[10px] font-mono text-[#64748B] uppercase tracking-wider">
          <span>STATION SWITCHER</span>
          <span>{stations.length} AWS</span>
        </div>

        <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
          {stations.map((s) => {
            const isSelected = location.pathname === `/stations/${s.station_id}`;

            let dotColor = '#10B981'; // Green
            if (s.status === 'DEGRADED') {
              dotColor = '#F59E0B'; // Amber
            } else if (s.status === 'OFFLINE') {
              dotColor = '#64748B'; // Gray
            }

            return (
              <button
                key={s.station_id}
                onClick={() => navigate(`/stations/${s.station_id}`)}
                className={`w-full text-left flex items-center justify-between px-2 py-1.5 rounded text-xs font-mono transition-colors ${
                  isSelected
                    ? 'bg-[#1A2234] text-sky-300 font-bold border-l-2 border-sky-400 pl-1.5'
                    : 'text-[#94A3B8] hover:bg-[#161F30] hover:text-[#F8FAFC]'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: dotColor }}
                  />
                  <span className="truncate">{s.station_id}</span>
                </div>
                <span className="text-[10px] text-[#64748B] shrink-0 font-normal">
                  {s.health_index || 90}%
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer / Architecture Badge */}
      <div className="p-2.5 border-t border-[#2D3748] text-[10px] font-mono text-[#64748B]">
        <div className="text-[#94A3B8]">SkyGuard AI v1.0</div>
        <div className="truncate">Hybrid Anomaly NOC</div>
      </div>
    </aside>
  );
};
