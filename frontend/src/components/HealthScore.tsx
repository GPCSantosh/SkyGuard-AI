/**
 * SkyGuard AI — Health Score Component
 * Clean numeric scoring (28px SemiBold) without radial gauges per anti-slop rules.
 */

import React from 'react';
import { getHealthBand } from '../utils/formatters';

interface HealthScoreProps {
  score: number;
  statusBand?: string;
  trend?: 'IMPROVING' | 'STABLE' | 'DEGRADING' | string;
  window?: string;
  size?: 'md' | 'lg';
  showDisclaimer?: boolean;
}

export const HealthScore: React.FC<HealthScoreProps> = ({
  score,
  statusBand,
  trend = 'STABLE',
  window: timeWindow = '7d',
  size = 'md',
  showDisclaimer = false,
}) => {
  const band = getHealthBand(score);
  const displayBand = statusBand || band.label;

  const trendGlyph =
    trend === 'IMPROVING' ? '↑' : trend === 'DEGRADING' ? '↓' : '→';

  const trendColor =
    trend === 'IMPROVING'
      ? 'text-emerald-400'
      : trend === 'DEGRADING'
      ? 'text-red-400'
      : 'text-[#94A3B8]';

  return (
    <div className="bg-[#111827] border border-[#2D3748] rounded p-3">
      <div className="flex items-center justify-between pb-1.5 border-b border-[#2D3748]/60 text-[11px] font-mono text-[#64748B] uppercase tracking-wider">
        <span>SENSOR HEALTH INDEX</span>
        <span>WINDOW: {timeWindow}</span>
      </div>

      <div className="flex items-baseline gap-3 my-2">
        <div
          className={`${
            size === 'lg' ? 'text-3xl' : 'text-2xl'
          } font-mono font-bold tracking-tight text-[#F8FAFC]`}
        >
          {score}
          <span className="text-xs text-[#64748B] font-normal ml-1">/ 100</span>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-mono font-semibold px-2 py-0.5 rounded border ${band.badgeClass}`}
          >
            {displayBand}
          </span>
          <span className={`text-xs font-mono flex items-center gap-0.5 ${trendColor}`}>
            <span>{trendGlyph}</span>
            <span>{trend}</span>
          </span>
        </div>
      </div>

      {showDisclaimer && (
        <div className="text-[11px] text-[#64748B] leading-tight border-t border-[#2D3748]/40 pt-2 mt-1">
          <strong>Scientific Notice:</strong> Health Index is an empirical reliability indicator computed across anomaly frequency, temporal stability, and telemetry liveness. It is not an uncalibrated hardware failure probability.
        </div>
      )}
    </div>
  );
};
