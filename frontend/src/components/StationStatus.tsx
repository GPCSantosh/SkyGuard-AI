import React from 'react';
import { StationOperationalStatus } from '../types/api';

interface StationStatusProps {
  status: StationOperationalStatus | string;
  showDot?: boolean;
}

export const StationStatus: React.FC<StationStatusProps> = ({ status, showDot = true }) => {
  let colorStyles = 'bg-slate-800 text-slate-300 border-slate-700';
  let dotColor = 'bg-slate-400';

  switch (status) {
    case 'ACTIVE':
      colorStyles = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
      dotColor = 'bg-emerald-400';
      break;
    case 'DEGRADED':
      colorStyles = 'bg-amber-950/60 text-amber-400 border-amber-800/80';
      dotColor = 'bg-amber-400';
      break;
    case 'MAINTENANCE':
      colorStyles = 'bg-indigo-950/60 text-indigo-400 border-indigo-800/80';
      dotColor = 'bg-indigo-400';
      break;
    case 'OFFLINE':
    case 'DECOMMISSIONED':
      colorStyles = 'bg-slate-900 text-slate-500 border-slate-800';
      dotColor = 'bg-slate-600';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono uppercase tracking-wider border ${colorStyles}`}
    >
      {showDot && <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />}
      {status}
    </span>
  );
};
