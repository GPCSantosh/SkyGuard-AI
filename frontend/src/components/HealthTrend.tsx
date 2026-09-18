/**
 * SkyGuard AI — Health Trend & 5-Component Breakdown Component
 * Visualizes the 5 component dimensions and 30-day degradation trend.
 */

import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { ComponentHealthScores } from '../types/api';

interface HealthTrendProps {
  componentScores: ComponentHealthScores;
  parameterHealth?: Record<
    string,
    { score: number; status: string; trend: string }
  >;
  history?: Array<{ timestamp: string; score: number }>;
}

export const HealthTrend: React.FC<HealthTrendProps> = ({
  componentScores,
  parameterHealth,
  history = [],
}) => {
  const components = [
    {
      key: 'anomaly_health',
      name: 'Anomaly Health',
      score: componentScores.anomaly_health,
      desc: 'Deduced from anomalous spike/drift frequency',
    },
    {
      key: 'data_quality_health',
      name: 'Data Quality / QC',
      score: componentScores.data_quality_health,
      desc: 'Deduced from missingness and bounds validity',
    },
    {
      key: 'communication_health',
      name: 'Communication Liveness',
      score: componentScores.communication_health,
      desc: 'Packet latency, gap duration, and out-of-order sequences',
    },
    {
      key: 'temporal_stability_health',
      name: 'Temporal Stability',
      score: componentScores.temporal_stability_health,
      desc: 'Flatline count and diurnal harmonic residual',
    },
    {
      key: 'spatial_consistency_health',
      name: 'Spatial Consistency',
      score: componentScores.spatial_consistency_health,
      desc: 'Consensus alignment with geographic neighbors',
    },
  ];

  return (
    <div className="space-y-4">
      {/* 5-Component Breakdown */}
      <div className="bg-[#111827] border border-[#2D3748] rounded p-3.5">
        <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#2D3748]">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#F8FAFC]">
            5-Component Reliability Breakdown
          </h4>
          <span className="text-[11px] font-mono text-[#64748B]">
            Empirical Dimensions (0-100)
          </span>
        </div>

        <div className="space-y-2.5">
          {components.map((comp) => {
            const barColor =
              comp.score >= 85
                ? 'bg-emerald-500'
                : comp.score >= 65
                ? 'bg-amber-500'
                : 'bg-red-500';

            return (
              <div key={comp.key} className="space-y-1">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-[#F8FAFC] font-medium">{comp.name}</span>
                  <span className="font-semibold text-[#38BDF8]">
                    {comp.score} <span className="text-[#64748B] text-[10px]">/ 100</span>
                  </span>
                </div>
                <div className="w-full bg-[#1A2234] h-2 rounded overflow-hidden flex border border-[#2D3748]/60">
                  <div
                    className={`h-full transition-all duration-300 rounded ${barColor}`}
                    style={{ width: `${comp.score}%` }}
                  />
                </div>
                <div className="text-[10px] text-[#64748B]">{comp.desc}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Parameter Channel Health */}
      {parameterHealth && (
        <div className="bg-[#111827] border border-[#2D3748] rounded p-3.5">
          <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-[#2D3748]">
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#F8FAFC]">
              Parameter-Level Sensor Status
            </h4>
            <span className="text-[11px] font-mono text-[#64748B]">Channel Isolation</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {Object.entries(parameterHealth).map(([param, info]) => {
              const label =
                param === 'temperature_c'
                  ? 'Temperature (°C)'
                  : param === 'humidity_pct'
                  ? 'Humidity (%)'
                  : 'Pressure (hPa)';

              const statusColor =
                info.status === 'HEALTHY'
                  ? 'text-emerald-400 border-emerald-800/60 bg-emerald-950/30'
                  : info.status === 'ATTENTION'
                  ? 'text-amber-400 border-amber-800/60 bg-amber-950/30'
                  : 'text-red-400 border-red-800/60 bg-red-950/30';

              return (
                <div key={param} className="bg-[#1A2234] border border-[#2D3748] rounded p-2.5">
                  <div className="text-[11px] font-mono text-[#94A3B8] truncate">{label}</div>
                  <div className="flex items-baseline justify-between mt-1">
                    <span className="text-lg font-mono font-bold text-[#F8FAFC]">
                      {info.score}
                    </span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${statusColor}`}>
                      {info.status}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-[#64748B] mt-1">
                    Trend: {info.trend}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 30-Day Health Trend Area Chart */}
      {history.length > 0 && (
        <div className="bg-[#111827] border border-[#2D3748] rounded p-3.5">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#2D3748]">
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#F8FAFC]">
              Health Index Trajectory (30-Day Trend)
            </h4>
            <span className="text-[11px] font-mono text-[#64748B]">Empirical Reliability Area</span>
          </div>

          <div style={{ width: '100%', height: 140 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="healthAreaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1F2937" strokeDasharray="3 3" opacity={0.5} />
                <XAxis
                  dataKey="timestamp"
                  stroke="#64748B"
                  tick={{ fontSize: 9, fontFamily: 'JetBrains Mono', fill: '#64748B' }}
                  tickLine={false}
                  axisLine={{ stroke: '#2D3748' }}
                  interval={5}
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="#64748B"
                  tick={{ fontSize: 9, fontFamily: 'JetBrains Mono', fill: '#64748B' }}
                  tickLine={false}
                  axisLine={{ stroke: '#2D3748' }}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    return (
                      <div className="bg-[#1A2234] border border-[#3D4F6B] p-2 rounded shadow text-xs font-mono">
                        <div className="text-[#94A3B8]">{label}</div>
                        <div className="text-emerald-400 font-bold">
                          Health: {payload[0].value} / 100
                        </div>
                      </div>
                    );
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="score"
                  stroke="#10B981"
                  strokeWidth={1.5}
                  fillOpacity={1}
                  fill="url(#healthAreaGrad)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
