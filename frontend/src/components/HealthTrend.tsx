import React from 'react';
import { HealthComponentScores, ParameterHealthScores } from '../types/api';

interface HealthTrendProps {
  components?: HealthComponentScores;
  parameterHealth?: ParameterHealthScores;
}

export const HealthTrend: React.FC<HealthTrendProps> = ({
  components,
  parameterHealth,
}) => {
  const componentItems = [
    { label: 'Anomaly Density', score: components?.anomaly_score ?? 100 },
    { label: 'Data Quality / QC', score: components?.data_quality_score ?? 100 },
    { label: 'Communication Liveness', score: components?.communication_score ?? 100 },
    { label: 'Temporal Stability', score: components?.temporal_stability_score ?? 100 },
    { label: 'Spatial Consistency', score: components?.spatial_consistency_score ?? 100 },
  ];

  const getScoreColor = (score: number) => {
    if (score < 60) return 'bg-red-500';
    if (score < 85) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  return (
    <div className="space-y-4">
      <div className="p-4 rounded border bg-surface-1 border-border">
        <h4 className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-3">
          5-Component Reliability Breakdown
        </h4>
        <div className="space-y-2.5">
          {componentItems.map((item) => (
            <div key={item.label} className="space-y-1">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-slate-300">{item.label}</span>
                <span className="text-slate-200 font-semibold">{Math.round(item.score)}/100</span>
              </div>
              <div className="w-full h-1.5 bg-surface-2 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getScoreColor(item.score)} transition-all duration-300`}
                  style={{ width: `${Math.min(Math.max(item.score, 0), 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {parameterHealth && (
        <div className="p-4 rounded border bg-surface-1 border-border">
          <h4 className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-3">
            Parameter-Level Sensor Status
          </h4>
          <div className="grid grid-cols-3 gap-3">
            <div className="p-2.5 rounded bg-surface-2 border border-border-subtle text-center">
              <span className="text-[10px] font-mono text-slate-400 block">TEMPERATURE</span>
              <span className="text-h2 font-mono font-semibold text-ops-weather">
                {parameterHealth.temperature_health !== null && parameterHealth.temperature_health !== undefined
                  ? `${Math.round(parameterHealth.temperature_health)}%`
                  : 'N/A'}
              </span>
            </div>
            <div className="p-2.5 rounded bg-surface-2 border border-border-subtle text-center">
              <span className="text-[10px] font-mono text-slate-400 block">HUMIDITY</span>
              <span className="text-h2 font-mono font-semibold text-ops-humidity">
                {parameterHealth.humidity_health !== null && parameterHealth.humidity_health !== undefined
                  ? `${Math.round(parameterHealth.humidity_health)}%`
                  : 'N/A'}
              </span>
            </div>
            <div className="p-2.5 rounded bg-surface-2 border border-border-subtle text-center">
              <span className="text-[10px] font-mono text-slate-400 block">PRESSURE</span>
              <span className="text-h2 font-mono font-semibold text-ops-pressure">
                {parameterHealth.pressure_health !== null && parameterHealth.pressure_health !== undefined
                  ? `${Math.round(parameterHealth.pressure_health)}%`
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
