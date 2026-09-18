/**
 * SkyGuard AI — Meteorological & Scientific Formatters
 * Consistent units, coordinate formatting, relative age, and semantic color lookups.
 */

import { DecisionSeverity, HybridDecisionType } from '../types/api';

export function formatTemperature(val: number | null | undefined, precision = 1): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${val.toFixed(precision)} °C`;
}

export function formatHumidity(val: number | null | undefined, precision = 1): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${val.toFixed(precision)} %`;
}

export function formatPressure(val: number | null | undefined, precision = 1): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${val.toFixed(precision)} hPa`;
}

export function formatCoordinates(lat: number, lon: number): string {
  const latDir = lat >= 0 ? '°N' : '°S';
  const lonDir = lon >= 0 ? '°E' : '°W';
  return `${Math.abs(lat).toFixed(4)}${latDir}  ${Math.abs(lon).toFixed(4)}${lonDir}`;
}

export function formatElevation(elevation?: number | null): string {
  if (elevation === null || elevation === undefined || isNaN(elevation)) return '—';
  return `el. ${elevation}m`;
}

export function formatUtcTime(timestamp?: string | null): string {
  if (!timestamp) return '—';
  try {
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return timestamp;
    return (
      d.toISOString().replace('T', ' ').substring(11, 19) + ' UTC'
    );
  } catch {
    return timestamp;
  }
}

export function formatUtcDate(timestamp?: string | null): string {
  if (!timestamp) return '—';
  try {
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return timestamp;
    return d.toISOString().replace('T', ' ').substring(0, 16) + ' UTC';
  } catch {
    return timestamp;
  }
}

export function formatRelativeAge(seconds?: number | null): string {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return '—';
  if (seconds < 60) return `${Math.floor(seconds)}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function getSeverityStyle(severity: DecisionSeverity): {
  bg: string;
  text: string;
  border: string;
  dot: string;
  accentBorder: string;
} {
  switch (severity) {
    case 'CRITICAL':
      return {
        bg: 'bg-[#450A0A]',
        text: 'text-[#FCA5A5]',
        border: 'border-[#7F1D1D]',
        dot: '#EF4444',
        accentBorder: 'border-l-[#EF4444]',
      };
    case 'HIGH':
      return {
        bg: 'bg-[#431407]',
        text: 'text-[#FDBA74]',
        border: 'border-[#7C2D12]',
        dot: '#F97316',
        accentBorder: 'border-l-[#F97316]',
      };
    case 'MEDIUM':
      return {
        bg: 'bg-[#451A03]',
        text: 'text-[#FDE68A]',
        border: 'border-[#78350F]',
        dot: '#F59E0B',
        accentBorder: 'border-l-[#F59E0B]',
      };
    case 'LOW':
      return {
        bg: 'bg-[#0C1A28]',
        text: 'text-[#7DD3FC]',
        border: 'border-[#164E63]',
        dot: '#38BDF8',
        accentBorder: 'border-l-[#38BDF8]',
      };
    case 'INFO':
    default:
      return {
        bg: 'bg-[#0F172A]',
        text: 'text-[#94A3B8]',
        border: 'border-[#334155]',
        dot: '#64748B',
        accentBorder: 'border-l-[#64748B]',
      };
  }
}

export function getDecisionBadge(decision: HybridDecisionType): {
  label: string;
  color: string;
  badgeClass: string;
} {
  switch (decision) {
    case 'PROBABLE_SENSOR_ANOMALY':
      return {
        label: 'PROBABLE_SENSOR_ANOMALY',
        color: '#EF4444',
        badgeClass: 'bg-red-950/80 text-red-300 border-red-800/80',
      };
    case 'PROBABLE_DATA_QUALITY_ISSUE':
      return {
        label: 'PROBABLE_DATA_QUALITY_ISSUE',
        color: '#F97316',
        badgeClass: 'bg-orange-950/80 text-orange-300 border-orange-800/80',
      };
    case 'POSSIBLE_GENUINE_EVENT':
      return {
        label: 'POSSIBLE_GENUINE_EVENT',
        color: '#6366F1',
        badgeClass: 'bg-indigo-950/80 text-indigo-300 border-indigo-800/80',
      };
    case 'UNCERTAIN':
      return {
        label: 'UNCERTAIN',
        color: '#EC4899',
        badgeClass: 'bg-pink-950/80 text-pink-300 border-pink-800/80',
      };
    case 'NORMAL':
    default:
      return {
        label: 'NORMAL',
        color: '#10B981',
        badgeClass: 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80',
      };
  }
}

export function getHealthBand(score: number): {
  label: 'HEALTHY' | 'GOOD' | 'ATTENTION' | 'DEGRADED' | 'CRITICAL';
  color: string;
  badgeClass: string;
} {
  if (score >= 90) {
    return {
      label: 'HEALTHY',
      color: '#10B981',
      badgeClass: 'bg-emerald-950/70 text-emerald-400 border-emerald-800/70',
    };
  }
  if (score >= 75) {
    return {
      label: 'GOOD',
      color: '#34D399',
      badgeClass: 'bg-emerald-950/50 text-emerald-300 border-emerald-800/50',
    };
  }
  if (score >= 60) {
    return {
      label: 'ATTENTION',
      color: '#F59E0B',
      badgeClass: 'bg-amber-950/70 text-amber-300 border-amber-800/70',
    };
  }
  if (score >= 40) {
    return {
      label: 'DEGRADED',
      color: '#F97316',
      badgeClass: 'bg-orange-950/80 text-orange-300 border-orange-800/80',
    };
  }
  return {
    label: 'CRITICAL',
    color: '#EF4444',
    badgeClass: 'bg-red-950/80 text-red-300 border-red-800/80',
  };
}
