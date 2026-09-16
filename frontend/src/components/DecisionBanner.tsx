import React from 'react';
import { HybridDecisionType, AlertSeverity } from '../types/api';
import { SeverityBadge } from './SeverityBadge';
import { ShieldAlert, CheckCircle2, CloudLightning, HelpCircle, AlertTriangle } from 'lucide-react';

interface DecisionBannerProps {
  decision: HybridDecisionType | string;
  severity: AlertSeverity | string;
  reasonCodes?: string[];
  stationId?: string;
  timestamp?: string;
  isDegradedMode?: boolean;
}

export const DecisionBanner: React.FC<DecisionBannerProps> = ({
  decision,
  severity,
  reasonCodes = [],
  stationId,
  timestamp,
  isDegradedMode = false,
}) => {
  let title = 'NOMINAL METEOROLOGICAL STATE';
  let bannerBorder = 'border-slate-700 bg-surface-1';
  let Icon = CheckCircle2;
  let iconColor = 'text-emerald-400';

  switch (decision) {
    case 'NORMAL':
      title = 'NOMINAL OBSERVATION — QC PASSED';
      bannerBorder = 'border-emerald-800/60 bg-emerald-950/20';
      Icon = CheckCircle2;
      iconColor = 'text-emerald-400';
      break;
    case 'POSSIBLE_GENUINE_EVENT':
      title = 'POSSIBLE GENUINE WEATHER EVENT';
      bannerBorder = 'border-indigo-700/70 bg-indigo-950/30';
      Icon = CloudLightning;
      iconColor = 'text-indigo-400';
      break;
    case 'PROBABLE_SENSOR_ANOMALY':
      title = 'PROBABLE SENSOR ANOMALY';
      bannerBorder = 'border-red-800/70 bg-red-950/30';
      Icon = ShieldAlert;
      iconColor = 'text-red-400';
      break;
    case 'PROBABLE_DATA_QUALITY_ISSUE':
      title = 'PROBABLE DATA QUALITY / TRANSMISSION ISSUE';
      bannerBorder = 'border-amber-800/70 bg-amber-950/30';
      Icon = AlertTriangle;
      iconColor = 'text-amber-400';
      break;
    case 'UNCERTAIN':
      title = 'UNCERTAIN OBSERVATION — OPERATOR REVIEW RECOMMENDED';
      bannerBorder = 'border-fuchsia-800/70 bg-fuchsia-950/30';
      Icon = HelpCircle;
      iconColor = 'text-fuchsia-400';
      break;
  }

  return (
    <div className={`p-4 rounded border ${bannerBorder} mb-4`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded bg-surface-2 border border-border-subtle ${iconColor}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-h2 font-semibold tracking-wide text-slate-100">{title}</span>
              <SeverityBadge severity={severity} />
              {isDegradedMode && (
                <span className="px-1.5 py-0.5 text-[10px] font-mono uppercase bg-amber-950 text-amber-300 border border-amber-800 rounded">
                  Degraded Mode
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-1 text-data text-slate-400">
              {stationId && <span>Station: <strong className="font-mono text-slate-200">{stationId}</strong></span>}
              {timestamp && <span>Timestamp: <span className="font-mono text-slate-300">{new Date(timestamp).toUTCString()}</span></span>}
            </div>
          </div>
        </div>

        {reasonCodes.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 max-w-md">
            <span className="text-[11px] text-slate-400 uppercase font-mono mr-1">Triggers:</span>
            {reasonCodes.map((code) => (
              <span
                key={code}
                className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-2 text-slate-300 border border-border"
              >
                {code}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
