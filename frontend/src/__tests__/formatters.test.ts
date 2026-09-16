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
} from '../utils/formatters';

describe('formatters unit tests', () => {
  test('formatTemperature formats floating precision cleanly', () => {
    expect(formatTemperature(32.628673268787495, 2, false)).toBe('32.63');
    expect(formatTemperature(32.628673268787495, 1, false)).toBe('32.6');
    expect(formatTemperature(32.628673268787495, 2, true)).toBe('32.63 °C');
    expect(formatTemperature(null)).toBe('--');
    expect(formatTemperature(undefined)).toBe('--');
  });

  test('formatHumidity formats to 1 decimal place', () => {
    expect(formatHumidity(48.94265346242501, 1, false)).toBe('48.9');
    expect(formatHumidity(48.94265346242501, 1, true)).toBe('48.9%');
    expect(formatHumidity(null)).toBe('--');
  });

  test('formatPressure formats barometric values to 2 decimals', () => {
    expect(formatPressure(1013.253456, 2, false)).toBe('1013.25');
    expect(formatPressure(1001.4001, 2, true)).toBe('1001.40 hPa');
    expect(formatPressure(null)).toBe('--');
  });

  test('formatCoordinates provides standard 4-decimal precision', () => {
    expect(formatCoordinates(28.5850123, 77.2060456)).toBe('28.5850°N, 77.2060°E');
    expect(formatCoordinates(-33.868812, 151.209345)).toBe('33.8688°S, 151.2093°E');
    expect(formatCoordinates(null, null)).toBe('--');
  });

  test('formatDistance formats distance in km', () => {
    expect(formatDistance(18.423)).toBe('18.4 km');
    expect(formatDistance(null)).toBe('--');
  });

  test('formatHealthScore rounds to integer', () => {
    expect(formatHealthScore(74.45)).toBe('74');
    expect(formatHealthScore(97.8)).toBe('98');
    expect(formatHealthScore(null)).toBe('--');
  });

  test('formatScore formats ML scores to 2 or 3 decimals', () => {
    expect(formatScore(0.81234, 2)).toBe('0.81');
    expect(formatScore(0.81234, 3)).toBe('0.812');
    expect(formatScore(null)).toBe('--');
  });

  test('formatContribution includes explicit plus or minus sign', () => {
    expect(formatContribution(0.4215, 3)).toBe('+0.422');
    expect(formatContribution(-0.1843, 3)).toBe('-0.184');
    expect(formatContribution(null)).toBe('--');
  });

  test('formatLatency formats milliseconds cleanly', () => {
    expect(formatLatency(0.2134)).toBe('0.21 ms');
    expect(formatLatency(5.894)).toBe('5.89 ms');
  });

  test('formatTelemetryValue auto-detects parameters', () => {
    expect(formatTelemetryValue('temperature_c', 31.1234, true)).toBe('31.12 °C');
    expect(formatTelemetryValue('relative_humidity_pct', 71.24, true)).toBe('71.2%');
    expect(formatTelemetryValue('sea_level_pressure_hpa', 1001.423, true)).toBe('1001.42 hPa');
  });

  test('formatIsoUtc produces standard readable UTC string', () => {
    const iso = '2026-09-17T14:16:43.000Z';
    expect(formatIsoUtc(iso)).toBe('2026-09-17 14:16:43 UTC');
  });

  test('formatAge calculates relative age', () => {
    expect(formatAge(12)).toBe('12s ago');
    expect(formatAge(180)).toBe('3m ago');
    expect(formatAge(7200)).toBe('2.0h ago');
  });
});
