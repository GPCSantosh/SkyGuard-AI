/**
 * SkyGuard AI — Decision Banner Component
 * Flagship sticky decision banner with trigger codes, severity accent, and provenance metadata.
 */

import React from 'react';
import { HybridDecisionType, DecisionSeverity } from '../types/api';
import { SeverityBadge } from './SeverityBadge';
import { getDecisionBadge, formatUtcTime } from '../utils/formatters';

interface DecisionBannerProps {
  decision: HybridDecisionType;
  severity: DecisionSeverity;
  stationId: string;
  stationName?: string;
  timestamp: string;
  durationMinutes?: number;
  engineVersion?: string;
  modelVersion?: string;
  explanationMethod?: string;
  triggerCodes?: string[];
  summary?: string;
}

export const DecisionBanner: React.FC<DecisionBannerProps> = ({
  decision,
  severity,
  stationId,
  stationName,
  timestamp,
  durationMinutes,
  engineVersion = 'hybrid_v1.0.0',
  modelVersion = 'isolation_forest_v1',
  explanationMethod = 'TREE_SHAP',
  triggerCodes = [],
  summary,
}) => {
  const decStyle = getDecisionBadge(decision);

  const borderAccentColor =
    severity === 'CRITICAL'
      ? 'border-l-red-500'
      : severity === 'HIGH'
      ? 'border-l-orange-500'
      : severity === 'MEDIUM'
      ? 'border-l-amber-500'
      : 'border-l-sky-500';

  return (
    <div
      className={`w-full bg-[#111827] border border-[#2D3748] border-l-4 ${borderAccentColor} p-3.5 rounded shadow-sm`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2.5 pb-2 border-b border-[#2D3748]/60">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span
            className="text-xs font-mono font-semibold px-2 py-0.5 rounded border"
            style={{
              borderColor: `${decStyle.color}50`,
              backgroundColor: `${decStyle.color}15`,
              color: decStyle.color,
            }}
          >
            {decision.replace(/_/g, ' ')}
          </span>
          <SeverityBadge severity={severity} />
          <span className="text-xs text-[#94A3B8]">
            Station <strong className="text-[#F8FAFC] font-mono">{stationId}</strong>
            {stationName && <span className="ml-1 text-[#64748B]">({stationName})</span>}
          </span>
          <span className="text-xs text-[#64748B]">·</span>
          <span className="text-xs font-mono text-[#94A3B8]">{formatUtcTime(timestamp)}</span>
          {durationMinutes !== undefined && (
            <span className="text-xs text-amber-400 bg-amber-950/40 border border-amber-900/60 px-1.5 py-0.5 rounded font-mono">
              Duration: {durationMinutes} min active
            </span>
          )}
        </div>

        {triggerCodes.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] uppercase font-mono text-[#64748B] tracking-wider">
              TRIGGERS:
            </span>
            {triggerCodes.map((code) => (
              <span
                key={code}
                className="text-[10px] font-mono bg-[#1A2234] text-[#94A3B8] border border-[#2D3748] px-1.5 py-0.5 rounded"
              >
                {code}
              </span>
            ))}
          </div>
        )}
      </div>

      {summary && (
        <p className="text-[13px] text-[#F8FAFC] mt-2.5 leading-relaxed">
          {summary}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 mt-2 pt-2 border-t border-[#2D3748]/40 text-[11px] font-mono text-[#64748B]">
        <div className="flex items-center gap-3">
          <span>
            engine: <span className="text-[#94A3B8]">{engineVersion}</span>
          </span>
          <span>·</span>
          <span>
            model: <span className="text-[#94A3B8]">{modelVersion}</span>
          </span>
          <span>·</span>
          <span>
            method: <span className="text-[#94A3B8]">{explanationMethod}</span>
          </span>
        </div>
        <div className="text-[#64748B]">
          SkyGuard AI Mission Control · Calibrated Anomaly Inference
        </div>
      </div>
    </div>
  );
};
