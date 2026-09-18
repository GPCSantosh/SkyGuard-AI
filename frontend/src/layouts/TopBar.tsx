/**
 * SkyGuard AI — Operations Center Top Status Bar
 * 40px fixed bar with live UTC clock, network health, active alerts, and connection state.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAnomalies } from '../hooks/useAnomalies';
import { useStations } from '../hooks/useStations';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { USE_MOCK_DATA } from '../api/client';

export const TopBar: React.FC = () => {
  const navigate = useNavigate();
  const { data: anomalies = [] } = useAnomalies();
  const { data: stations = [] } = useStations();
  const { connectionState } = useRealtimeStream();

  // Dynamic UTC Clock
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const h = String(now.getUTCHours()).padStart(2, '0');
      const m = String(now.getUTCMinutes()).padStart(2, '0');
      const s = String(now.getUTCSeconds()).padStart(2, '0');
      setUtcTime(`${h}:${m}:${s} UTC`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const totalStations = stations.length;
  const operationalStations = stations.filter(
    (s) => s.status === 'ACTIVE' || s.status === 'DEGRADED'
  ).length;

  const activeAlertsCount = anomalies.length;
  const hasCritical = anomalies.some((a) => a.severity === 'CRITICAL');
  const hasHigh = anomalies.some((a) => a.severity === 'HIGH');

  // Connection indicator styling
  const isWsConnected = connectionState === 'CONNECTED';
  const connColor = isWsConnected ? '#10B981' : '#F59E0B';

  return (
    <header className="h-10 bg-[#0B0F17] border-b border-[#2D3748] px-3 flex items-center justify-between text-xs font-mono select-none sticky top-0 z-50">
      {/* Left: Product Mark & Operational Mode */}
      <div className="flex items-center gap-2.5">
        <div
          onClick={() => navigate('/network')}
          className="flex items-center gap-1.5 cursor-pointer group"
        >
          <span className="text-sky-400 font-bold text-sm tracking-wider group-hover:text-sky-300">
            ◈ SKYGUARD AI
          </span>
          <span className="text-[10px] text-[#64748B] px-1 py-0.2 bg-[#1A2234] border border-[#2D3748] rounded">
            NOC v1.0
          </span>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 ml-2 border-l border-[#2D3748] pl-2.5 text-[11px]">
          <span className="text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-1.5 py-0.5 rounded">
            ((•)) LIVE MODE
          </span>
          {USE_MOCK_DATA && (
            <span className="text-amber-400 bg-amber-950/60 border border-amber-800/80 px-1.5 py-0.5 rounded text-[10px]">
              DEMO / SYNTHETIC VALIDATION
            </span>
          )}
        </div>
      </div>

      {/* Center: Live Stream & Network Health */}
      <div className="hidden md:flex items-center gap-3 text-[11px]">
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#111827] border border-[#2D3748]">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: connColor }}
          />
          <span className="text-[#94A3B8]">
            {isWsConnected
              ? 'LIVE STREAM · WEBSOCKET'
              : 'LIVE STREAM · POLLING (15s)'}
          </span>
        </div>

        <div className="text-[#94A3B8]">
          NETWORK:{' '}
          <strong className="text-[#F8FAFC]">
            {operationalStations}/{totalStations || 8} OPERATIONAL
          </strong>
        </div>
      </div>

      {/* Right: Active Alerts Badge & UTC Clock */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={() => navigate('/history')}
          className={`flex items-center px-2.5 py-0.5 rounded border transition-colors ${
            hasCritical
              ? 'bg-red-950 text-red-300 border-red-800 hover:bg-red-900/60'
              : hasHigh || activeAlertsCount > 0
              ? 'bg-amber-950/80 text-amber-300 border-amber-800 hover:bg-amber-900/60'
              : 'bg-[#111827] text-[#94A3B8] border-[#2D3748]'
          }`}
        >
          <span className="font-bold uppercase">{activeAlertsCount} ALERTS</span>
        </button>

        <div className="text-[#94A3B8] font-mono text-[11px] px-2 py-0.5 rounded bg-[#111827] border border-[#2D3748] tracking-widest">
          {utcTime || '00:00:00 UTC'}
        </div>
      </div>
    </header>
  );
};
