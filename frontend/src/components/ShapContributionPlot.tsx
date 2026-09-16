import React from 'react';
import { FeatureContribution } from '../types/api';
import { formatContribution, formatScore } from '../utils/formatters';
import { Cpu, HelpCircle } from 'lucide-react';

interface ShapContributionPlotProps {
  contributions: FeatureContribution[];
  method?: string;
  anomalyScore?: number;
  threshold?: number;
}

/**
 * Converts technical feature names into readable human-friendly titles.
 */
function humanizeFeatureName(name: string): string {
  const map: Record<string, string> = {
    temp_rate_of_change: 'Temperature Rate of Change',
    temp_zscore_1h: 'Temperature Z-Score (1h)',
    pressure_delta_nbr: 'Pressure Neighbor Departure',
    humidity_consistency: 'Relative Humidity Consistency',
    temp_diurnal_residual: 'Diurnal Cycle Residual',
    temp_spatial_deviation: 'Temperature Spatial Deviation',
    pressure_rate_of_change: 'Pressure Rate of Change',
    dew_point_depression: 'Dew Point Depression',
    humidity_rate_of_change: 'Humidity Rate of Change',
    temporal_volatility: 'Temporal Volatility Index',
  };
  if (map[name]) return map[name];
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export const ShapContributionPlot: React.FC<ShapContributionPlotProps> = ({
  contributions = [],
  method = 'TREE_SHAP',
  anomalyScore,
  threshold,
}) => {
  // Sort contributions by absolute magnitude descending
  const sorted = [...contributions].sort((a, b) => {
    const scoreA = Math.abs(a.contribution ?? a.contribution_score ?? 0);
    const scoreB = Math.abs(b.contribution ?? b.contribution_score ?? 0);
    return scoreB - scoreA;
  });

  const maxAbsScore = Math.max(
    ...sorted.map((c) => Math.abs(c.contribution ?? c.contribution_score ?? 0)),
    0.001
  );

  return (
    <div className="p-4 rounded border border-border bg-surface-1 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2.5">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-ops-pressure" />
          <h3 className="text-h2 font-semibold text-slate-100">
            ML Feature Attribution Analysis ({method})
          </h3>
        </div>

        {(anomalyScore !== undefined || threshold !== undefined) && (
          <div className="flex items-center gap-3 text-[11px] font-mono">
            {anomalyScore !== undefined && (
              <span className="text-slate-400">
                Score: <strong className="text-red-400">{formatScore(anomalyScore, 3)}</strong>
              </span>
            )}
            {threshold !== undefined && (
              <span className="text-slate-400">
                Threshold: <strong className="text-slate-200">{formatScore(threshold, 3)}</strong>
              </span>
            )}
          </div>
        )}
      </div>

      {sorted.length === 0 ? (
        <div className="py-4 text-center text-slate-400 font-mono text-data italic">
          No individual feature attribution records available for this model inference.
        </div>
      ) : (
        <div className="space-y-2.5">
          {sorted.map((feat, idx) => {
            const score = feat.contribution ?? feat.contribution_score ?? 0;
            const isPositive = score > 0;
            const rank = feat.rank ?? idx + 1;
            const dirStr = String(feat.direction || '').toLowerCase();
            const increases = dirStr.includes('increase') || isPositive;
            const pct = Math.min(100, Math.round((Math.abs(score) / maxAbsScore) * 100));

            return (
              <div
                key={feat.feature_name}
                className="p-2.5 rounded bg-surface-2 border border-border-subtle hover:border-border-emphasis transition-colors"
              >
                {/* Header line for feature */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 flex items-center justify-center rounded bg-surface-1 border border-border text-[10px] font-mono text-slate-400 font-bold">
                      #{rank}
                    </span>
                    <div>
                      <span className="text-data font-semibold text-slate-200">
                        {humanizeFeatureName(feat.feature_name)}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 ml-2">
                        [{feat.feature_name}]
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 font-mono text-[11px]">
                    {feat.feature_value !== undefined && feat.feature_value !== null && (
                      <span className="text-slate-400">
                        Value: <strong className="text-slate-200">{typeof feat.feature_value === 'number' ? feat.feature_value.toFixed(2) : String(feat.feature_value)}</strong>
                      </span>
                    )}
                    <span
                      className={`font-bold px-1.5 py-0.5 rounded text-[10px] border ${
                        increases
                          ? 'text-red-300 bg-red-950/70 border-red-800'
                          : 'text-emerald-300 bg-emerald-950/70 border-emerald-800'
                      }`}
                    >
                      {formatContribution(score, 3)}
                    </span>
                  </div>
                </div>

                {/* Horizontal Bar Visualizer */}
                <div className="space-y-1">
                  <div className="w-full h-2 rounded bg-surface-1 overflow-hidden flex">
                    {increases ? (
                      <div
                        className="h-full bg-red-500 rounded transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    ) : (
                      <div
                        className="h-full bg-emerald-500 rounded transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    )}
                  </div>
                  <div className="flex justify-between items-center text-[9px] font-mono text-slate-500">
                    <span>
                      {increases ? '▲ Increases Anomaly Score' : '▼ Decreases Anomaly Score'}
                    </span>
                    <span>Magnitude: {pct}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Scientific & Non-Causality Disclaimer (Strict requirement) */}
      <div className="flex items-start gap-1.5 p-2 rounded bg-surface-2/40 border border-border-subtle text-[10px] text-slate-400">
        <HelpCircle className="w-3.5 h-3.5 text-slate-500 flex-shrink-0 mt-0.5" />
        <span>
          <strong className="text-slate-300">Operational Notice:</strong> SHAP feature attribution reflects statistical model decision boundaries and mathematical variance contributions. Feature attributions indicate which variables pushed the anomaly score above the calibrated threshold, but do not assert physical hardware causality.
        </span>
      </div>
    </div>
  );
};
