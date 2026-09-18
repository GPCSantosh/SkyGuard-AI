/**
 * SkyGuard AI — Data Freshness Indicator
 * Visual age badge with color coding: Green (<1 int), Amber (1-3 int), Red (>3 int).
 */

import React from 'react';
import { formatRelativeAge } from '../utils/formatters';

interface DataFreshnessIndicatorProps {
  lastUpdateSeconds?: number | null;
  expectedIntervalSeconds?: number;
  timestamp?: string | null;
  showTextPrefix?: boolean;
}

export const DataFreshnessIndicator: React.FC<DataFreshnessIndicatorProps> = ({
  lastUpdateSeconds,
  expectedIntervalSeconds = 300,
  showTextPrefix = true,
}) => {
  const age = lastUpdateSeconds ?? 15;

  let state: 'fresh' | 'stale' | 'critical' = 'fresh';
  if (age > expectedIntervalSeconds * 3) {
    state = 'critical';
  } else if (age > expectedIntervalSeconds) {
    state = 'stale';
  }

  const dotColor =
    state === 'fresh' ? '#10B981' : state === 'stale' ? '#F59E0B' : '#EF4444';

  const textColor =
    state === 'fresh'
      ? 'text-[#94A3B8]'
      : state === 'stale'
      ? 'text-amber-300'
      : 'text-red-400';

  return (
    <span className={`inline-flex items-center gap-1.5 font-mono text-[11px] ${textColor}`}>
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ backgroundColor: dotColor }}
        aria-hidden="true"
      />
      <span>
        {showTextPrefix && 'Updated '}
        {formatRelativeAge(age)}
        {state === 'stale' && ' (stale)'}
        {state === 'critical' && ' (offline)'}
      </span>
    </span>
  );
};
