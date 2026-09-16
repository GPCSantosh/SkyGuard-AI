import React from 'react';
import { SystemHealthStatus } from '../types/api';
import { CheckCircle2, AlertTriangle } from 'lucide-react';

interface SystemStatusProps {
  status?: SystemHealthStatus;
  isLoading?: boolean;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({
  status,
  isLoading = false,
}) => {
  if (isLoading || !status) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 bg-surface-2 animate-pulse rounded border border-border-subtle" />
        ))}
      </div>
    );
  }

  const subsystems = [
    { label: 'Database Service', val: status.database_status, ok: status.database_status === 'CONNECTED' },
    { label: 'ML Model Registry', val: status.model_registry_status, ok: status.model_registry_status === 'LOADED' },
    { label: 'Active Model', val: status.active_model_id, ok: true, mono: true },
    { label: 'Spatial Topology', val: `${status.spatial_topology_stations_count} Nodes`, ok: status.spatial_topology_stations_count > 0 },
    { label: 'Replay Simulator', val: status.replay_simulator_status, ok: true },
    { label: 'Mean Latency', val: `${status.mean_pipeline_latency_ms} ms`, ok: status.mean_pipeline_latency_ms < 50 },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {subsystems.map((sub) => (
        <div key={sub.label} className="p-3 rounded border border-border bg-surface-1">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>{sub.label}</span>
            {sub.ok ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            )}
          </div>
          <div className={`mt-1.5 text-h2 font-semibold ${sub.mono ? 'font-mono text-slate-300 text-[13px]' : 'text-slate-100'}`}>
            {sub.val}
          </div>
        </div>
      ))}
    </div>
  );
};
