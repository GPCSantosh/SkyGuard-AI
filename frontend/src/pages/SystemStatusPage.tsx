import React from 'react';
import { useSystemHealth, useReplayStatus, useStepReplay } from '../hooks/useSystem';
import { SystemStatus } from '../components/SystemStatus';
import { Cpu, Play, FastForward, CheckCircle2, Server } from 'lucide-react';

export const SystemStatusPage: React.FC = () => {
  const { data: systemHealth, isLoading } = useSystemHealth();
  const { data: replayStatus } = useReplayStatus();
  const stepMutation = useStepReplay();

  const handleStepReplay = (count: number) => {
    stepMutation.mutate(count);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="p-3 rounded border border-border bg-surface-1 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-ops-weather" />
          <div>
            <h1 className="text-h1 font-bold font-mono text-slate-100">
              System Health & Pipeline Observability
            </h1>
            <span className="text-[11px] font-mono text-slate-400">
              Subsystem status, end-to-end latency metrics, and simulation controls
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400">
            Uptime: <strong className="text-slate-100">{systemHealth?.uptime_seconds ? `${(systemHealth.uptime_seconds / 3600).toFixed(1)} hrs` : '--'}</strong>
          </span>
        </div>
      </div>

      {/* Subsystem Metric Cards Grid */}
      <SystemStatus status={systemHealth} isLoading={isLoading} />

      {/* 2-Column: Processing Pipeline Profile + Operational Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Core Pipeline Telemetry */}
        <div className="p-4 rounded border border-border bg-surface-1 space-y-3">
          <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
            <Server className="w-4 h-4 text-ops-weather" />
            Pipeline Execution Profile
          </h3>

          <div className="space-y-2 font-mono text-data">
            <div className="flex justify-between p-2 rounded bg-surface-2 border border-border-subtle">
              <span className="text-slate-400">Total Processed Observations:</span>
              <span className="text-slate-100 font-semibold">{systemHealth?.total_observations_processed ?? 0}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-surface-2 border border-border-subtle">
              <span className="text-slate-400">Active Monitored Stations:</span>
              <span className="text-slate-100 font-semibold">{systemHealth?.active_monitored_stations ?? 0}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-surface-2 border border-border-subtle">
              <span className="text-slate-400">Mean Pipeline Latency:</span>
              <span className="text-emerald-400 font-semibold">{systemHealth?.mean_pipeline_latency_ms ?? 0} ms</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-surface-2 border border-border-subtle">
              <span className="text-slate-400">Active ML Model ID:</span>
              <span className="text-ops-pressure font-semibold">{systemHealth?.active_model_id ?? 'N/A'}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-surface-2 border border-border-subtle">
              <span className="text-slate-400">Last Observation Processed:</span>
              <span className="text-slate-300">
                {systemHealth?.last_processed_timestamp
                  ? new Date(systemHealth.last_processed_timestamp).toUTCString()
                  : '--'}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Stream Replay Simulation Controls (Clearly demarcated) */}
        <div className="p-4 rounded border border-indigo-900/60 bg-indigo-950/20 space-y-3">
          <div className="flex items-center justify-between border-b border-indigo-900/50 pb-2">
            <h3 className="text-h2 font-semibold text-indigo-300 flex items-center gap-2">
              <FastForward className="w-4 h-4 text-indigo-400" />
              Stream Replay Simulation Engine
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 uppercase">
              Isolated Test Mode
            </span>
          </div>

          <p className="text-data text-slate-300 leading-snug">
            Step historical observations and synthetic fault injections through the full real-time pipeline to test anomaly triggers, explainability attributions, and advisory corrections.
          </p>

          <div className="grid grid-cols-2 gap-3 py-1 font-mono text-[11px]">
            <div className="p-2.5 rounded bg-surface-2 border border-border-subtle">
              <span className="text-slate-400 block">Queued Stream Data</span>
              <span className="text-h2 font-bold text-slate-100">
                {replayStatus?.total_queued_observations ?? 0}
              </span>
            </div>
            <div className="p-2.5 rounded bg-surface-2 border border-border-subtle">
              <span className="text-slate-400 block">Emitted Timesteps</span>
              <span className="text-h2 font-bold text-ops-weather">
                {replayStatus?.emitted_count ?? 0}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => handleStepReplay(1)}
              disabled={stepMutation.isPending}
              className="flex-1 py-2 px-3 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-slate-100 text-data font-mono font-medium flex items-center justify-center gap-2 transition-colors"
            >
              <Play className="w-4 h-4" />
              Step 1 Observation
            </button>

            <button
              onClick={() => handleStepReplay(10)}
              disabled={stepMutation.isPending}
              className="flex-1 py-2 px-3 rounded bg-surface-2 hover:bg-surface-hover border border-border disabled:opacity-50 text-slate-200 text-data font-mono font-medium flex items-center justify-center gap-2 transition-colors"
            >
              <FastForward className="w-4 h-4 text-indigo-400" />
              Step 10 Observations
            </button>
          </div>

          {stepMutation.isSuccess && (
            <div className="p-2 rounded bg-emerald-950/50 border border-emerald-800 text-[11px] font-mono text-emerald-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Processed {stepMutation.data?.steps_executed} steps through pipeline. Total emitted: {stepMutation.data?.total_emitted}.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
