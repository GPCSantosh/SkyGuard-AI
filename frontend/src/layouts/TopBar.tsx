import React, { useState, useEffect } from 'react';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { useAnomalies } from '../hooks/useAnomalies';
import { DataFreshnessIndicator } from '../components/DataFreshnessIndicator';
import { Shield, Bell, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const TopBar: React.FC = () => {
  const navigate = useNavigate();
  const streamState = useRealtimeStream();
  const { data: anomalyData } = useAnomalies({ limit: 100 });
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const totalAnomalies = anomalyData?.pagination?.total_count ?? 0;

  return (
    <header className="h-10 bg-surface-1 border-b border-border px-4 flex items-center justify-between text-xs select-none z-30 flex-shrink-0">
      {/* Brand & Network Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/network')}>
          <Shield className="w-4 h-4 text-ops-weather" />
          <span className="font-semibold tracking-wider font-mono text-slate-100 uppercase">
            SkyGuard AI
          </span>
          <span className="text-[10px] font-mono text-slate-400 bg-surface-2 px-1.5 py-0.5 rounded border border-border-subtle hidden sm:inline">
            NOC v1.0
          </span>
        </div>
      </div>

      {/* Center: Realtime Telemetry Status */}
      <div className="flex items-center gap-3">
        <DataFreshnessIndicator
          isConnected={streamState.isConnected}
          secondsSinceLastUpdate={streamState.secondsSinceLastUpdate}
          lastHeartbeat={streamState.lastHeartbeat}
        />
      </div>

      {/* Right: Clock & Quick Alert Counter */}
      <div className="flex items-center gap-4">
        {/* Active Alert Trigger Pill */}
        <button
          onClick={() => navigate('/anomalies')}
          className={`flex items-center gap-1.5 px-2 py-0.5 rounded font-mono text-[11px] border transition-colors ${
            totalAnomalies > 0
              ? 'bg-red-950/60 text-red-300 border-red-800 hover:bg-red-900/60'
              : 'bg-surface-2 text-slate-400 border-border-subtle'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>{totalAnomalies} ALERTS</span>
        </button>

        {/* Live UTC Clock */}
        <div className="flex items-center gap-1.5 text-slate-300 font-mono text-[11px] bg-surface-2 px-2 py-0.5 rounded border border-border-subtle">
          <Clock className="w-3.5 h-3.5 text-ops-weather" />
          <span>{utcTime || '--:--:-- UTC'}</span>
        </div>
      </div>
    </header>
  );
};
