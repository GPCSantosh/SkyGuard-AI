import React, { useState } from 'react';
import { NavLink, useNavigate, useParams, useLocation } from 'react-router-dom';
import { useStations } from '../hooks/useStations';
import {
  Network,
  Activity,
  Radio,
  AlertTriangle,
  HeartPulse,
  GitCompare,
  History,
  Cpu,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const { data: stations = [] } = useStations();
  const navigate = useNavigate();
  const { stationId: routeStationId } = useParams<{ stationId?: string }>();
  const location = useLocation();

  // Determine active station from route or first configured station
  const defaultStationId = stations.length > 0 ? stations[0].station_id : '';
  const activeStationId = routeStationId || defaultStationId;

  const navItems = [
    { to: '/network', label: 'Network Overview', icon: Network },
    { to: '/live', label: 'Live Monitoring', icon: Activity },
    {
      to: activeStationId ? `/stations/${activeStationId}` : '/network',
      label: 'Station Details',
      icon: Radio,
      activeMatch: (pathname: string) => pathname.startsWith('/stations'),
    },
    {
      to: '/anomalies',
      label: 'Anomaly Investigation',
      icon: AlertTriangle,
      activeMatch: (pathname: string) => pathname.startsWith('/anomalies'),
    },
    { to: '/health', label: 'Sensor Health', icon: HeartPulse },
    { to: '/corrections', label: 'Correction Review', icon: GitCompare },
    { to: '/history', label: 'Historical Analysis', icon: History },
    { to: '/system', label: 'System Status', icon: Cpu },
  ];

  // Sort stations by severity/health
  const sortedStations = [...stations].sort((a, b) => {
    const healthA = a.latest_snapshot?.latest_health_score ?? 100;
    const healthB = b.latest_snapshot?.latest_health_score ?? 100;
    return healthA - healthB;
  });

  return (
    <aside
      className={`h-[calc(100vh-40px)] bg-surface-1 border-r border-border flex flex-col justify-between transition-all duration-200 select-none z-20 flex-shrink-0 ${
        collapsed ? 'w-12' : 'w-56'
      }`}
    >
      {/* Top Section: Main Navigation Routes */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        <nav className="p-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isMatch = item.activeMatch
              ? item.activeMatch(location.pathname)
              : location.pathname === item.to;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-2.5 py-2 rounded text-data font-medium transition-colors ${
                  isMatch
                    ? 'bg-surface-2 text-ops-weather border-l-2 border-l-ops-weather'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-hover'
                }`}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>

        {/* Live Station State Strip (Severity-Sorted) */}
        {!collapsed && sortedStations.length > 0 && (
          <div className="px-2 pt-3 border-t border-border-subtle">
            <div className="px-2 pb-1.5 flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-wider">
              <span>Stations ({sortedStations.length})</span>
              <span>Health</span>
            </div>
            <div className="space-y-0.5 max-h-56 overflow-y-auto pr-1">
              {sortedStations.map((stn) => {
                const score = stn.latest_snapshot?.latest_health_score ?? 100;
                const isSelected = activeStationId === stn.station_id && location.pathname.startsWith('/stations');
                const anomCount = stn.latest_snapshot?.active_anomaly_count_24h ?? 0;

                let scoreColor = 'text-emerald-400';
                let dotColor = 'bg-emerald-400';
                if (score < 60) {
                  scoreColor = 'text-red-400';
                  dotColor = 'bg-red-400';
                } else if (score < 85) {
                  scoreColor = 'text-amber-400';
                  dotColor = 'bg-amber-400';
                }

                return (
                  <button
                    key={stn.station_id}
                    onClick={() => navigate(`/stations/${stn.station_id}`)}
                    className={`w-full flex items-center justify-between px-2 py-1 rounded text-left text-[11px] font-mono transition-colors ${
                      isSelected
                        ? 'bg-surface-2 text-ops-weather font-semibold border-l-2 border-l-ops-weather'
                        : 'text-slate-300 hover:bg-surface-hover'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 truncate">
                      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotColor}`} />
                      <span className="truncate">{stn.station_id}</span>
                      {anomCount > 0 && (
                        <span className="px-1 text-[9px] bg-red-950 text-red-300 rounded border border-red-800">
                          {anomCount}
                        </span>
                      )}
                    </div>
                    <span className={`font-medium ${scoreColor}`}>{Math.round(score)}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Footer / Collapse Toggle */}
      <div className="p-2 border-t border-border-subtle bg-surface-1/80">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-1.5 rounded hover:bg-surface-hover text-slate-400 hover:text-slate-200 transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
};
