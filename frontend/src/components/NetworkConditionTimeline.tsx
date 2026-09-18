/**
 * SkyGuard AI — Horizontal Network Condition Timeline
 * Visualizes 24-hour network-wide operational status, health continuity, and incident episodes.
 */

import React from 'react';

interface TimelineSegment {
  hourLabel: string;
  status: 'NOMINAL' | 'INCIDENT' | 'DEGRADED';
  incidentCount: number;
  avgHealth: number;
  timestamp: string;
}

export const NetworkConditionTimeline: React.FC = () => {
  // Generate 24 continuous hourly slots for the last 24h
  const segments: TimelineSegment[] = Array.from({ length: 24 }).map((_, i) => {
    const hour = (new Date().getUTCHours() - (23 - i) + 24) % 24;
    const hourLabel = `${hour.toString().padStart(2, '0')}:00`;
    
    // Simulate slight incident in slot 18 and 21 for realistic analytical variation
    let status: 'NOMINAL' | 'INCIDENT' | 'DEGRADED' = 'NOMINAL';
    let incidentCount = 0;
    let avgHealth = 96;

    if (i === 17) {
      status = 'DEGRADED';
      incidentCount = 1;
      avgHealth = 78;
    } else if (i === 21) {
      status = 'INCIDENT';
      incidentCount = 2;
      avgHealth = 64;
    } else if (i === 22 || i === 23) {
      status = 'DEGRADED';
      incidentCount = 1;
      avgHealth = 82;
    }

    return {
      hourLabel,
      status,
      incidentCount,
      avgHealth,
      timestamp: `${hourLabel} UTC`,
    };
  });

  return (
    <div className="bg-[#0D131F] border border-[#1E293B] rounded p-3 text-xs font-mono space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
        <span className="text-[#94A3B8] font-bold uppercase tracking-wider">
          24-HOUR SYNOPTIC HEALTH & TELEMETRY CONTINUITY TIMELINE
        </span>

        <div className="flex items-center gap-3 text-[10px] text-[#94A3B8]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-emerald-500/80" />
            Nominal (95–100%)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-amber-500/80" />
            Degraded / Minor Anomaly
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-red-500/80" />
            Critical Inconsistency
          </span>
          <span className="text-sky-400 font-bold ml-1">99.82% Uptime</span>
        </div>
      </div>

      {/* 24-Block Bar Strip */}
      <div className="grid grid-cols-12 sm:grid-cols-24 gap-1 pt-1">
        {segments.map((seg, idx) => {
          let bgClass = 'bg-emerald-500/30 hover:bg-emerald-500/60 border-emerald-700/50';
          if (seg.status === 'INCIDENT') {
            bgClass = 'bg-red-500/50 hover:bg-red-500/80 border-red-700/80 animate-pulse';
          } else if (seg.status === 'DEGRADED') {
            bgClass = 'bg-amber-500/40 hover:bg-amber-500/70 border-amber-700/60';
          }

          return (
            <div
              key={idx}
              className={`group relative h-7 rounded-sm border ${bgClass} transition-all cursor-pointer flex items-center justify-center`}
            >
              <span className="text-[8px] text-[#94A3B8] opacity-60 group-hover:opacity-100">
                {idx % 4 === 0 ? seg.hourLabel.slice(0, 2) : ''}
              </span>

              {/* Hover Tooltip */}
              <div className="absolute bottom-9 left-1/2 -translate-x-1/2 hidden group-hover:block z-30 bg-[#0B0F17] border border-[#334155] rounded px-2.5 py-1.5 shadow-2xl text-[10px] whitespace-nowrap pointer-events-none">
                <div className="font-bold text-sky-300">{seg.timestamp}</div>
                <div className="text-[#F8FAFC]">Status: {seg.status}</div>
                <div className="text-[#94A3B8]">Health: {seg.avgHealth}% | Anomalies: {seg.incidentCount}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-between text-[9px] text-[#64748B] pt-0.5">
        <span>-24 Hours</span>
        <span>-12 Hours</span>
        <span>-6 Hours</span>
        <span>Current (Live)</span>
      </div>
    </div>
  );
};
