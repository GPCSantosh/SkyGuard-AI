import assert from 'node:assert';
import {
  formatTemperature,
  formatHumidity,
  formatPressure,
  formatCoordinates,
  formatDistance,
  formatHealthScore,
  formatScore,
  formatContribution,
  formatLatency,
  formatTelemetryValue,
  formatIsoUtc,
  formatAge,
} from '../utils/formatters.js';

console.log('--- Running SkyGuard Frontend Unit Tests ---');

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

// Test 4: Coordinate formatting
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

// Test 7: ML Anomaly Score formatting
assert.strictEqual(formatScore(0.81234, 2), '0.81');
assert.strictEqual(formatScore(0.81234, 3), '0.812');
assert.strictEqual(formatScore(null), '--');
console.log('✓ formatScore passed');

// Test 8: SHAP contribution formatting
assert.strictEqual(formatContribution(0.4215, 3), '+0.422');
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

console.log('==================================================');
console.log('ALL FRONTEND FORMATTER TESTS PASSED (12/12)');
console.log('==================================================');
