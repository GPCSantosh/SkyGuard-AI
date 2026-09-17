import React, { useState, useEffect } from 'react';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { useAnomalies } from '../hooks/useAnomalies';
import { useReplayStatus, useLiveSourceHealth } from '../hooks/useSystem';
import { DataFreshnessIndicator } from '../components/DataFreshnessIndicator';
import { EvidenceAuditModal } from '../components/EvidenceAuditModal';
import { Shield, Bell, Clock, Award, PlayCircle, Radio } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const TopBar: React.FC = () => {
  const navigate = useNavigate();
  const streamState = useRealtimeStream();
  const { data: anomalyData } = useAnomalies({ limit: 100 });
  const { data: replayStatus } = useReplayStatus();
  const { data: liveSource } = useLiveSourceHealth();
  const [utcTime, setUtcTime] = useState<string>('');
  const [isEvidenceModalOpen, setIsEvidenceModalOpen] = useState<boolean>(false);

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
  const isDemoReplay = (replayStatus?.emitted_count ?? 0) > 0 || replayStatus?.is_running;
  const liveUnavailable = liveSource?.status === 'AUTH_ERROR' || liveSource?.status === 'CONFIG_ERROR' || liveSource?.status === 'RATE_LIMITED';

  return (
    <>
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

          {/* Operational Mode Pill */}
          <div className="hidden md:flex items-center gap-1.5 font-mono text-[10px]">
            {isDemoReplay ? (
              <span className="bg-indigo-950/80 text-indigo-300 border border-indigo-700/60 px-2 py-0.5 rounded flex items-center gap-1">
                <PlayCircle className="w-3 h-3 text-indigo-400" />
                DEMO REPLAY MODE
              </span>
            ) : liveUnavailable ? (
              <span className="bg-red-950/80 text-red-300 border border-red-700/60 px-2 py-0.5 rounded flex items-center gap-1">
                <Radio className="w-3 h-3 text-red-400" />
                LIVE SOURCE UNAVAILABLE
              </span>
            ) : (
              <span className="bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 px-2 py-0.5 rounded flex items-center gap-1">
                <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
                LIVE MODE (OPEN-METEO)
              </span>
            )}
          </div>
        </div>

        {/* Center: Realtime Telemetry Status */}
        <div className="flex items-center gap-3">
          <DataFreshnessIndicator
            isConnected={streamState.isConnected}
            secondsSinceLastUpdate={streamState.secondsSinceLastUpdate}
            lastHeartbeat={streamState.lastHeartbeat}
            connectionStatus={streamState.connectionStatus}
            transportMode={streamState.transportMode}
          />
        </div>

        {/* Right: Evidence, Clock & Quick Alert Counter */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Scientific Evidence & Provenance Trigger */}
          <button
            onClick={() => setIsEvidenceModalOpen(true)}
            className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[11px] bg-surface-2 hover:bg-surface-3 text-slate-300 border border-border-subtle transition-colors"
            title="Inspect Benchmark Evidence & Provenance"
          >
            <Award className="w-3.5 h-3.5 text-ops-weather" />
            <span>EVIDENCE</span>
          </button>

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

      {/* Evidence and Scientific Provenance Modal */}
      <EvidenceAuditModal
        isOpen={isEvidenceModalOpen}
        onClose={() => setIsEvidenceModalOpen(false)}
      />
    </>
  );
};
