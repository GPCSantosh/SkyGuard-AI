/**
 * Telemetry and Meteorological Number Formatting Utilities
 * Prevents excessive floating-point precision leaks and maintains presentation consistency.
 * Underlying raw values are never mutated.
 */

/**
 * Format ambient or dew point temperature in Celsius (°C).
 * Typically 1 or 2 decimal places.
 */
export function formatTemperature(
  val?: number | null,
  decimals: number = 2,
  includeUnit: boolean = false
): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(decimals);
  return includeUnit ? `${formatted} °C` : formatted;
}

/**
 * Format relative humidity percentage (%).
 * Typically 1 decimal place or whole integer.
 */
export function formatHumidity(
  val?: number | null,
  decimals: number = 1,
  includeUnit: boolean = false
): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(decimals);
  return includeUnit ? `${formatted}%` : formatted;
}

/**
 * Format barometric / atmospheric pressure in hPa.
 * Typically 2 decimal places.
 */
export function formatPressure(
  val?: number | null,
  decimals: number = 2,
  includeUnit: boolean = false
): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(decimals);
  return includeUnit ? `${formatted} hPa` : formatted;
}

/**
 * Format geodetic coordinates to standard geographical precision (4 decimal places).
 */
export function formatCoordinates(lat?: number | null, lon?: number | null): string {
  if (lat === null || lat === undefined || lon === null || lon === undefined) return '--';
  const latDir = lat >= 0 ? '°N' : '°S';
  const lonDir = lon >= 0 ? '°E' : '°W';
  return `${Math.abs(lat).toFixed(4)}${latDir}, ${Math.abs(lon).toFixed(4)}${lonDir}`;
}

/**
 * Format distance in kilometers (km) (1 decimal place).
 */
export function formatDistance(val?: number | null, includeUnit: boolean = true): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(1);
  return includeUnit ? `${formatted} km` : formatted;
}

/**
 * Format continuous health reliability score (0-100) (integer).
 */
export function formatHealthScore(val?: number | null): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  return Math.round(val).toString();
}

/**
 * Format ML anomaly / decision score (0.00 - 1.00) (2 or 3 decimals).
 */
export function formatScore(val?: number | null, decimals: number = 2): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  return val.toFixed(decimals);
}

/**
 * Format SHAP feature contribution value with explicit sign.
 */
export function formatContribution(val?: number | null, decimals: number = 3): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(decimals)}`;
}

/**
 * Format latency in milliseconds (ms) (2 decimals).
 */
export function formatLatency(val?: number | null): string {
  if (val === null || val === undefined || isNaN(val)) return '--';
  return `${val.toFixed(2)} ms`;
}

/**
 * Automatically format a known meteorological parameter by key name.
 */
export function formatTelemetryValue(
  paramKey: string,
  val?: number | null,
  includeUnit: boolean = true
): string {
  const lower = paramKey.toLowerCase();
  if (lower.includes('temp') || lower.includes('dew')) {
    return formatTemperature(val, 2, includeUnit);
  }
  if (lower.includes('hum') || lower.includes('rh')) {
    return formatHumidity(val, 1, includeUnit);
  }
  if (lower.includes('pres') || lower.includes('slp') || lower.includes('baro')) {
    return formatPressure(val, 2, includeUnit);
  }
  if (lower.includes('lat') || lower.includes('lon')) {
    return val !== null && val !== undefined ? val.toFixed(4) : '--';
  }
  if (lower.includes('elev')) {
    return val !== null && val !== undefined ? `${Math.round(val)} m` : '--';
  }
  if (typeof val === 'number') {
    return val.toFixed(2);
  }
  return String(val ?? '--');
}

/**
 * Format ISO 8601 UTC timestamp for display.
 */
export function formatIsoUtc(timestamp?: string | null, includeSeconds: boolean = true): string {
  if (!timestamp) return '--';
  try {
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return String(timestamp);
    const iso = d.toISOString();
    return includeSeconds
      ? iso.replace('T', ' ').substring(0, 19) + ' UTC'
      : iso.replace('T', ' ').substring(0, 16) + ' UTC';
  } catch {
    return String(timestamp);
  }
}

/**
 * Format elapsed time / age in seconds to human operational format.
 */
export function formatAge(seconds?: number | null): string {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  return `${(seconds / 3600).toFixed(1)}h ago`;
}
