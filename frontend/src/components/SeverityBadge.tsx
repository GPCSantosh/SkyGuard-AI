/**
 * SkyGuard AI — Severity Badge Component
 * Strict 4px rounded badge per UI_DESIGN_SYSTEM.md (never rounded-full).
 */

import React from 'react';
import { DecisionSeverity } from '../types/api';
import { getSeverityStyle } from '../utils/formatters';

interface SeverityBadgeProps {
  severity: DecisionSeverity;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  size = 'md',
}) => {
  const style = getSeverityStyle(severity);

  const pad = size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-[11px]';

  return (
    <span
      className={`inline-block font-mono font-medium tracking-wider border rounded ${style.bg} ${style.text} ${style.border} ${pad} select-none uppercase`}
    >
      {severity}
    </span>
  );
};
