/**
 * SkyGuard AI — Station Status Component
 * Displays ACTIVE / DEGRADED / OFFLINE badge with severity dot and text.
 */

import React from 'react';
import { StationStatusType } from '../types/api';

interface StationStatusProps {
  status: StationStatusType | string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const StationStatus: React.FC<StationStatusProps> = ({
  status,
  size = 'md',
  showLabel = true,
}) => {
  const norm = (status || 'ACTIVE').toUpperCase();

  let dotColor = '#10B981'; // Green (Active/Normal)
  let badgeClass = 'bg-emerald-950/70 text-emerald-300 border-emerald-800/80';
  let label = 'ACTIVE';

  if (norm === 'DEGRADED' || norm === 'WARNING' || norm === 'ATTENTION') {
    dotColor = '#F59E0B'; // Amber
    badgeClass = 'bg-amber-950/70 text-amber-300 border-amber-800/80';
    label = norm === 'WARNING' ? 'WARNING' : 'DEGRADED';
  } else if (norm === 'CRITICAL') {
    dotColor = '#EF4444'; // Red
    badgeClass = 'bg-red-950/70 text-red-300 border-red-800/80';
    label = 'CRITICAL';
  } else if (norm === 'OFFLINE' || norm === 'GAP' || norm === 'DISCONNECTED') {
    dotColor = '#64748B'; // Gray
    badgeClass = 'bg-slate-900/90 text-slate-400 border-slate-700/80';
    label = 'OFFLINE';
  }

  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : size === 'lg' ? 'w-2.5 h-2.5' : 'w-2 h-2';
  const textClass =
    size === 'sm'
      ? 'text-[10px] px-1.5 py-0.5'
      : size === 'lg'
      ? 'text-xs px-2.5 py-1 font-semibold'
      : 'text-[11px] px-2 py-0.5';

  return (
    <span
      className={`inline-flex items-center gap-1.5 border rounded ${badgeClass} ${textClass} font-mono tracking-wider uppercase select-none`}
    >
      <span
        className={`rounded-full shrink-0 ${dotSize}`}
        style={{ backgroundColor: dotColor }}
        aria-hidden="true"
      />
      {showLabel && <span>{label}</span>}
    </span>
  );
};
