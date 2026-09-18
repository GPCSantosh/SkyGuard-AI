/**
 * SkyGuard AI — TreeSHAP Feature Attribution Plot
 * Ranked horizontal attribution bars with directional impact (increases / decreases anomaly).
 */

import React from 'react';
import { FeatureContribution } from '../types/api';

interface ShapContributionPlotProps {
  contributions: FeatureContribution[];
  score?: number;
  threshold?: number;
}

export const ShapContributionPlot: React.FC<ShapContributionPlotProps> = ({
  contributions,
  score = 0.81,
  threshold = 0.58,
}) => {
  // Sort by absolute magnitude descending
  const sorted = [...contributions].sort(
    (a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)
  );

  const maxAbs = Math.max(
    ...sorted.map((c) => Math.abs(c.contribution)),
    0.1
  );

  return (
    <div className="w-full bg-[#111827] border border-[#2D3748] rounded p-3.5">
      <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#2D3748]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-indigo-400" />
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#F8FAFC]">
            ML Feature Attribution Analysis (TREE_SHAP)
          </h4>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-[#94A3B8]">
            Score:{' '}
            <strong className="text-red-400 font-semibold">
              {score.toFixed(3)}
            </strong>
          </span>
          <span className="text-[#64748B]">
            Threshold: <strong className="text-[#F8FAFC]">{threshold.toFixed(2)}</strong>
          </span>
        </div>
      </div>

      <div className="space-y-2.5">
        {sorted.map((item, idx) => {
          const isIncrease = item.direction === 'increases_anomaly';
          const pct = Math.min(100, (Math.abs(item.contribution) / maxAbs) * 100);

          return (
            <div key={idx} className="space-y-1">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#F8FAFC] font-medium">
                  {item.display_name || item.feature}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[#64748B] text-[11px]">
                    val: {item.value}
                  </span>
                  <span
                    className={`font-semibold ${
                      isIncrease ? 'text-amber-400' : 'text-emerald-400'
                    }`}
                  >
                    {item.contribution > 0 ? `+${item.contribution.toFixed(3)}` : item.contribution.toFixed(3)}
                  </span>
                  <span
                    className={`text-[10px] px-1 py-0.2 rounded border ${
                      isIncrease
                        ? 'bg-amber-950/40 text-amber-300 border-amber-800/50'
                        : 'bg-emerald-950/40 text-emerald-300 border-emerald-800/50'
                    }`}
                  >
                    {isIncrease ? '↑ increases anomaly' : '↓ decreases anomaly'}
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-[#1A2234] h-2 rounded overflow-hidden flex border border-[#2D3748]/50">
                <div
                  className={`h-full transition-all duration-300 rounded ${
                    isIncrease ? 'bg-amber-500/80' : 'bg-emerald-500/80'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              {item.description && (
                <div className="text-[11px] text-[#64748B] pl-0.5">
                  {item.description}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-2 border-t border-[#2D3748]/60 text-[11px] text-[#64748B] leading-normal">
        <strong>Notice:</strong> Feature attribution values represent mathematical SHAP contributions to the Isolation Forest anomaly partition. They do not claim physical fault causation.
      </div>
    </div>
  );
};
