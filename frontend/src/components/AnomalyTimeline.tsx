import React from 'react';
import { formatUtcTime } from '../utils/formatters';

interface AnomalyTimelineProps {
  firstDetected: string;
  peakDeviation?: string;
  lastObservation: string;
  isRecovered?: boolean;
  peakValue?: string;
}

export const AnomalyTimeline: React.FC<AnomalyTimelineProps> = ({
  firstDetected,
  peakDeviation,
  lastObservation,
  isRecovered = false,
  peakValue = '+6.2 °C',
}) => {
  const startTimestamp = firstDetected || new Date(Date.now() - 3600000).toISOString();
  const peakTimestamp = peakDeviation || new Date(Date.now() - 1800000).toISOString();
  const currentTimestamp = lastObservation || new Date().toISOString();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between border-b border-[#2D3748] pb-1.5">
        <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F8FAFC]">
          Chronological Anomaly Evolution
        </h4>
        <span className="text-[11px] font-mono text-[#64748B]">
          Timeline Resolution: 1 min
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Onset Stage */}
        <div className="bg-[#1A2234] border border-[#2D3748] rounded p-2.5">
          <div className="text-amber-400 text-xs font-mono font-semibold mb-1 uppercase">
            <span>ANOMALY ONSET / TRIGGER</span>
          </div>
          <div className="text-xs font-mono text-[#F8FAFC]">
            {formatUtcTime(startTimestamp)}
          </div>
          <div className="text-[11px] text-[#64748B] mt-0.5">
            Initial sudden deviation spike detected
          </div>
        </div>

        {/* Peak Stage */}
        <div className="bg-[#1A2234] border border-red-900/60 rounded p-2.5">
          <div className="text-red-400 text-xs font-mono font-semibold mb-1 uppercase">
            <span>PEAK DEVIATION</span>
          </div>
          <div className="text-xs font-mono text-[#F8FAFC] flex items-center justify-between">
            <span>{formatUtcTime(peakTimestamp)}</span>
            <span className="text-red-400 font-bold">{peakValue}</span>
          </div>
          <div className="text-[11px] text-[#64748B] mt-0.5">
            Max divergence from physical baseline
          </div>
        </div>

        {/* Current State */}
        <div className="bg-[#1A2234] border border-[#2D3748] rounded p-2.5">
          <div className="text-sky-400 text-xs font-mono font-semibold mb-1 uppercase">
            <span>{isRecovered ? 'RECOVERED / CLOSED' : 'CURRENT ACTIVE STATE'}</span>
          </div>
          <div className="text-xs font-mono text-[#F8FAFC]">
            {formatUtcTime(currentTimestamp)}
          </div>
          <div className="text-[11px] text-[#64748B] mt-0.5">
            {isRecovered ? 'Sensor returned to nominal limits' : 'Under active supervisory monitoring'}
          </div>
        </div>
      </div>
    </div>
  );
};
