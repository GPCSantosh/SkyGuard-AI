/**
 * SkyGuard AI — Historical & Real-Time Observation Telemetry Mock Generator
 * Strictly preserves missing values, causal timestamps, dual-signal raw vs imputed lines.
 */

import { WeatherObservation } from '../types/api';
import { MOCK_STATIONS } from './mockStations';

export function generateStationHistory(
  stationId: string,
  window: '6h' | '24h' | '7d' | '30d' = '24h'
): WeatherObservation[] {
  const station = MOCK_STATIONS.find((s) => s.station_id === stationId) || MOCK_STATIONS[0];
  const results: WeatherObservation[] = [];

  const now = new Date('2026-09-17T13:05:00Z').getTime();

  let stepMinutes = 5;
  let count = 288; // 24 hours at 5-min intervals

  if (window === '6h') {
    stepMinutes = 5;
    count = 72;
  } else if (window === '24h') {
    stepMinutes = 15;
    count = 96;
  } else if (window === '7d') {
    stepMinutes = 60;
    count = 168;
  } else if (window === '30d') {
    stepMinutes = 180;
    count = 240;
  }

  const baseTemp = 26.5;
  const baseHumidity = 58.0;
  const basePressure = station.elevation_m && station.elevation_m > 300 ? 982.0 : 1013.2;

  for (let i = count - 1; i >= 0; i--) {
    const timeMs = now - i * stepMinutes * 60 * 1000;
    const date = new Date(timeMs);
    const hour = date.getUTCHours() + date.getUTCMinutes() / 60;

    // Diurnal solar cycle
    const diurnalSolar = Math.sin(((hour - 9) / 24) * 2 * Math.PI);
    const nominalTemp = baseTemp + diurnalSolar * 6.5;
    const nominalHumidity = Math.max(20, Math.min(95, baseHumidity - diurnalSolar * 22.0));
    const semiDiurnalPressure = basePressure + Math.sin((hour / 12) * 2 * Math.PI) * 1.8;

    let rawTemp: number | null = parseFloat(nominalTemp.toFixed(1));
    let rawHumidity: number | null = parseFloat(nominalHumidity.toFixed(1));
    let rawPressure: number | null = parseFloat(semiDiurnalPressure.toFixed(1));

    let imputedTemp: number | null = null;
    let imputedHumidity: number | null = null;
    let imputedPressure: number | null = null;

    let isAnomalous = false;
    let decision: WeatherObservation['anomaly_decision'] = 'NORMAL';
    let severity: WeatherObservation['anomaly_severity'] = 'INFO';

    // Inject exact spike seen in screenshots for Safdarjung station 42182099999 near 12:10 - 13:05
    if (stationId === '42182099999' && i >= 0 && i <= 8) {
      if (i === 1 || i === 2) {
        rawTemp = 58.5; // Extreme sensor departure
        rawHumidity = 10.0;
        imputedTemp = parseFloat((baseTemp + 0.8).toFixed(1));
        imputedHumidity = parseFloat((baseHumidity + 2.0).toFixed(1));
        isAnomalous = true;
        decision = 'UNCERTAIN';
        severity = 'MEDIUM';
      } else if (i === 0) {
        rawTemp = 52.0;
        imputedTemp = 26.8;
        isAnomalous = true;
        decision = 'PROBABLE_SENSOR_ANOMALY';
        severity = 'HIGH';
      }
    }

    // Inject pressure anomaly for AWS_007
    if (stationId === 'AWS_007' && i <= 10 && i >= 3) {
      rawPressure = 1001.4;
      imputedPressure = 1012.9;
      isAnomalous = true;
      decision = 'PROBABLE_SENSOR_ANOMALY';
      severity = 'HIGH';
    }

    // Offline gap simulation for AWS_019
    if (stationId === 'AWS_019' && i <= 15) {
      rawTemp = null;
      rawHumidity = null;
      rawPressure = null;
    }

    results.push({
      station_id: stationId,
      station_name: station.station_name,
      timestamp: date.toISOString(),
      temperature_c: rawTemp,
      humidity_pct: rawHumidity,
      pressure_hpa: rawPressure,
      dew_point_c: rawTemp ? rawTemp - (100 - (rawHumidity || 50)) / 5 : null,
      data_quality_status: rawTemp === null ? 'GAP' : isAnomalous ? 'WARNING' : 'VALID',
      imputed_temperature_c: imputedTemp,
      imputed_humidity_pct: imputedHumidity,
      imputed_pressure_hpa: imputedPressure,
      neighbor_median_temperature_c: parseFloat((nominalTemp + 0.3).toFixed(1)),
      neighbor_median_humidity_pct: parseFloat((nominalHumidity + 0.5).toFixed(1)),
      neighbor_median_pressure_hpa: parseFloat((semiDiurnalPressure + 0.2).toFixed(1)),
      is_anomalous: isAnomalous,
      anomaly_decision: decision,
      anomaly_severity: severity,
    });
  }

  return results;
}
