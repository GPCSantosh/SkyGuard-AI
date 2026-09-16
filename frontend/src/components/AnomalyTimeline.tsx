import React from 'react';
import { formatIsoUtc } from '../utils/formatters';
import { Clock, AlertTriangle, CheckCircle2, Flame } from 'lucide-react';

export interface TimelineMilestone {
  label: string;
  timestamp?: string | null;
  value?: number | null;
  score?: number | null;
  status: 'onset' | 'peak' | 'active' | 'recovery' | 'normal';
}

interface AnomalyTimelineProps {
  onsetTimestamp?: string | null;
  peakTimestamp?: string | null;
  recoveryTimestamp?: string | null;
  currentTimestamp?: string | null;
  durationMinutes?: number | null;
  peakValue?: number | null;
  targetVariable?: string;
  unit?: string;
}

export const AnomalyTimeline: React.FC<AnomalyTimelineProps> = ({
  onsetTimestamp,
  peakTimestamp,
  recoveryTimestamp,
  currentTimestamp,
  durationMinutes,
  peakValue,
  targetVariable = 'Temperature',
  unit = '°C',
}) => {
  const milestones: TimelineMilestone[] = [
    {
      label: 'Episode Onset',
      timestamp: onsetTimestamp || currentTimestamp,
      status: 'onset',
    },
    {
      label: 'Peak Deviation',
      timestamp: peakTimestamp || currentTimestamp,
      value: peakValue,
      status: 'peak',
    },
    {
      label: recoveryTimestamp ? 'Recovery' : 'Current State',
      timestamp: recoveryTimestamp || currentTimestamp,
      status: recoveryTimestamp ? 'recovery' : 'active',
    },
  ];

  return (
    <div className="p-4 rounded border border-border bg-surface-1 space-y-3">
      <div className="flex items-center justify-between border-b border-border-subtle pb-2">
        <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
          <Clock className="w-4 h-4 text-ops-weather" />
          Anomaly Episode Reconstruction ({targetVariable})
        </h3>
        {durationMinutes !== undefined && durationMinutes !== null && (
          <span className="text-[11px] font-mono text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800">
            Duration: {durationMinutes.toFixed(0)} min active
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2 pt-1 font-mono">
        {milestones.map((m, idx) => {
          let badgeBorder = 'border-border-subtle bg-surface-2';
          let icon = <Clock className="w-3.5 h-3.5 text-slate-400" />;
          let labelColor = 'text-slate-300';

          if (m.status === 'onset') {
            badgeBorder = 'border-amber-800 bg-amber-950/30';
            icon = <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
            labelColor = 'text-amber-300';
          } else if (m.status === 'peak') {
            badgeBorder = 'border-red-800 bg-red-950/30';
            icon = <Flame className="w-3.5 h-3.5 text-red-400" />;
            labelColor = 'text-red-300';
          } else if (m.status === 'active') {
            badgeBorder = 'border-red-800/80 bg-red-950/40';
            icon = <AlertTriangle className="w-3.5 h-3.5 text-red-400" />;
            labelColor = 'text-red-300';
          } else if (m.status === 'recovery') {
            badgeBorder = 'border-emerald-800 bg-emerald-950/30';
            icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
            labelColor = 'text-emerald-300';
          }

          return (
            <div
              key={idx}
              className={`p-2.5 rounded border ${badgeBorder} flex flex-col justify-between text-left`}
            >
              <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider mb-1">
                {icon}
                <span className={`font-semibold ${labelColor}`}>{m.label}</span>
              </div>
              <div className="text-[11px] text-slate-200 font-bold truncate">
                {m.timestamp ? formatIsoUtc(m.timestamp, false) : '--'}
              </div>
              {m.value !== undefined && m.value !== null && (
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Peak: <span className="text-red-400 font-semibold">{m.value.toFixed(1)} {unit}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
