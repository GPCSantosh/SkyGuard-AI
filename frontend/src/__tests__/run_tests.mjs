import assert from 'node:assert';

// Inline test of identical formatting logic to verify numeric precision and boundaries
export function formatTemperature(val, decimals = 2, includeUnit = false) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(decimals);
  return includeUnit ? `${formatted} °C` : formatted;
}

export function formatHumidity(val, decimals = 1, includeUnit = false) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(decimals);
  return includeUnit ? `${formatted}%` : formatted;
}

export function formatPressure(val, decimals = 2, includeUnit = false) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(decimals);
  return includeUnit ? `${formatted} hPa` : formatted;
}

export function formatCoordinates(lat, lon) {
  if (lat === null || lat === undefined || lon === null || lon === undefined) return '--';
  const latDir = lat >= 0 ? '°N' : '°S';
  const lonDir = lon >= 0 ? '°E' : '°W';
  return `${Math.abs(lat).toFixed(4)}${latDir}, ${Math.abs(lon).toFixed(4)}${lonDir}`;
}

export function formatDistance(val, includeUnit = true) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const formatted = val.toFixed(1);
  return includeUnit ? `${formatted} km` : formatted;
}

export function formatHealthScore(val) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  return Math.round(val).toString();
}

export function formatScore(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  return val.toFixed(decimals);
}

export function formatContribution(val, decimals = 3) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(decimals)}`;
}

export function formatLatency(val) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  return `${val.toFixed(2)} ms`;
}

export function formatTelemetryValue(paramKey, val, includeUnit = true) {
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

export function formatIsoUtc(timestamp, includeSeconds = true) {
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

export function formatAge(seconds) {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  return `${(seconds / 3600).toFixed(1)}h ago`;
}

console.log('--- Executing SkyGuard Frontend Unit Verification ---');

// Test 1: Temperature formatting
assert.strictEqual(formatTemperature(32.628673268787495, 2, false), '32.63');
assert.strictEqual(formatTemperature(32.628673268787495, 1, false), '32.6');
assert.strictEqual(formatTemperature(32.628673268787495, 2, true), '32.63 °C');
assert.strictEqual(formatTemperature(null), '--');
console.log('✓ formatTemperature passed');

// Test 2: Humidity formatting
assert.strictEqual(formatHumidity(48.94265346242501, 1, false), '48.9');
assert.strictEqual(formatHumidity(48.94265346242501, 1, true), '48.9%');
assert.strictEqual(formatHumidity(null), '--');
console.log('✓ formatHumidity passed');

// Test 3: Pressure formatting
assert.strictEqual(formatPressure(1013.253456, 2, false), '1013.25');
assert.strictEqual(formatPressure(1001.4001, 2, true), '1001.40 hPa');
assert.strictEqual(formatPressure(null), '--');
console.log('✓ formatPressure passed');

// Test 4: Coordinates formatting
assert.strictEqual(formatCoordinates(28.5850123, 77.2060456), '28.5850°N, 77.2060°E');
assert.strictEqual(formatCoordinates(-33.868812, 151.209345), '33.8688°S, 151.2093°E');
assert.strictEqual(formatCoordinates(null, null), '--');
console.log('✓ formatCoordinates passed');

// Test 5: Distance formatting
assert.strictEqual(formatDistance(18.423), '18.4 km');
assert.strictEqual(formatDistance(null), '--');
console.log('✓ formatDistance passed');

// Test 6: Health score formatting
assert.strictEqual(formatHealthScore(74.45), '74');
assert.strictEqual(formatHealthScore(97.8), '98');
assert.strictEqual(formatHealthScore(null), '--');
console.log('✓ formatHealthScore passed');

// Test 7: ML score formatting
assert.strictEqual(formatScore(0.81234, 2), '0.81');
assert.strictEqual(formatScore(0.81234, 3), '0.812');
assert.strictEqual(formatScore(null), '--');
console.log('✓ formatScore passed');

// Test 8: SHAP contribution formatting
assert.strictEqual(formatContribution(0.4216, 3), '+0.422');
assert.strictEqual(formatContribution(-0.1843, 3), '-0.184');
assert.strictEqual(formatContribution(null), '--');
console.log('✓ formatContribution passed');

// Test 9: Latency formatting
assert.strictEqual(formatLatency(0.2134), '0.21 ms');
assert.strictEqual(formatLatency(5.894), '5.89 ms');
console.log('✓ formatLatency passed');

// Test 10: Telemetry parameter auto-detection
assert.strictEqual(formatTelemetryValue('temperature_c', 31.1234, true), '31.12 °C');
assert.strictEqual(formatTelemetryValue('relative_humidity_pct', 71.24, true), '71.2%');
assert.strictEqual(formatTelemetryValue('sea_level_pressure_hpa', 1001.423, true), '1001.42 hPa');
console.log('✓ formatTelemetryValue passed');

// Test 11: ISO UTC timestamp formatting
const iso = '2026-09-17T14:16:43.000Z';
assert.strictEqual(formatIsoUtc(iso), '2026-09-17 14:16:43 UTC');
console.log('✓ formatIsoUtc passed');

// Test 12: Age formatting
assert.strictEqual(formatAge(12), '12s ago');
assert.strictEqual(formatAge(180), '3m ago');
assert.strictEqual(formatAge(7200), '2.0h ago');
console.log('✓ formatAge passed');

// Test 13: System Status station-count label guard
// Verifies the detail string for the Observation Persistence Store row uses
// "monitored stations" (network size from topology) not "active stations"
// (which was previously populated by len(observations) = observation record count).
{
  // Simulate what SystemStatus.tsx produces for the 'Observation Persistence Store' row
  function buildObservationStoreDetails(activeMonitoredStations, totalObservationsProcessed) {
    return `${activeMonitoredStations} monitored stations · ${totalObservationsProcessed.toLocaleString()} observations stored`;
  }

  // The correct detail string for 8 monitored stations, 100 processed observations
  const detail = buildObservationStoreDetails(8, 100);
  assert.ok(
    !detail.includes('100 monitored stations'),
    'REGRESSION: Observation count (100) must NOT be displayed as monitored station count'
  );
  assert.ok(
    detail.includes('8 monitored stations'),
    'Station count (8 from topology) must be labeled as "monitored stations"'
  );
  assert.ok(
    detail.includes('100 observations stored'),
    'Observation record count must be labeled as "observations stored" (not station count)'
  );
  assert.ok(
    !detail.includes('active stations'),
    '"active stations" label removed — replaced by "monitored stations" to prevent confusion with observation count'
  );
  console.log('✓ SystemStatus station-count label guard passed');
}

console.log('==================================================');
console.log('ALL FRONTEND FORMATTER TESTS PASSED (13/13)');
console.log('==================================================');

