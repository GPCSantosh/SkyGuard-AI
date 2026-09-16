import React from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export interface TimelineStep {
  timestamp: string;
  isAnomaly: boolean;
  value: number;
  label?: string;
}

interface AnomalyTimelineProps {
  steps: TimelineStep[];
  unit?: string;
}

export const AnomalyTimeline: React.FC<AnomalyTimelineProps> = ({
  steps,
  unit = '°C',
}) => {
  if (steps.length === 0) return null;

  return (
    <div className="p-4 rounded border border-border bg-surface-1">
      <h3 className="text-h2 font-semibold text-slate-100 mb-3">
        Temporal Sequence Timeline
      </h3>
      <div className="flex items-center overflow-x-auto py-2 gap-2">
        {steps.map((step, idx) => (
          <div
            key={idx}
            className={`flex flex-col items-center min-w-[70px] p-2 rounded border text-center transition-all ${
              step.isAnomaly
                ? 'border-red-700 bg-red-950/40 text-red-200 ring-1 ring-red-500/50'
                : 'border-border-subtle bg-surface-2 text-slate-300'
            }`}
          >
            <span className="text-[10px] font-mono text-slate-400">
              {new Date(step.timestamp).toISOString().substring(11, 16)}Z
            </span>
            <div className="my-1">
              {step.isAnomaly ? (
                <AlertCircle className="w-4 h-4 text-red-400" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              )}
            </div>
            <span className="text-data font-mono font-semibold">
              {step.value.toFixed(1)}{unit}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
