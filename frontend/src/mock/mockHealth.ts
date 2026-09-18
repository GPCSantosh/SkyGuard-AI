/**
 * SkyGuard AI — Sensor Health Index & Reliability Scores Mock Data
 * Continuous 0-100 degradation scoring across 5 component dimensions.
 */

import { SensorHealthSummary } from '../types/api';
import { MOCK_STATIONS } from './mockStations';

export function getMockStationHealth(stationId: string): SensorHealthSummary {
  const station = MOCK_STATIONS.find((s) => s.station_id === stationId) || MOCK_STATIONS[0];

  let healthIndex = 95;
  let status: SensorHealthSummary['health_status'] = 'HEALTHY';
  let trend: SensorHealthSummary['health_trend'] = 'STABLE';
  let recommendation: SensorHealthSummary['maintenance_recommendation'] = 'NO_ACTION';

  let scores = {
    anomaly_health: 98,
    data_quality_health: 100,
    communication_health: 100,
    temporal_stability_health: 96,
    spatial_consistency_health: 95,
  };

  if (stationId === '42182099999') {
    healthIndex = 87;
    status = 'GOOD';
    trend = 'STABLE';
    recommendation = 'MONITOR';
    scores = {
      anomaly_health: 82,
      data_quality_health: 98,
      communication_health: 100,
      temporal_stability_health: 79,
      spatial_consistency_health: 84,
    };
  } else if (stationId === 'AWS_007') {
    healthIndex = 74;
    status = 'ATTENTION';
    trend = 'DEGRADING';
    recommendation = 'ROUTINE_CALIBRATION';
    scores = {
      anomaly_health: 68,
      data_quality_health: 90,
      communication_health: 100,
      temporal_stability_health: 72,
      spatial_consistency_health: 58,
    };
  } else if (stationId === 'AWS_014') {
    healthIndex = 43;
    status = 'DEGRADED';
    trend = 'DEGRADING';
    recommendation = 'PRIORITY_INSPECTION';
    scores = {
      anomaly_health: 31,
      data_quality_health: 80,
      communication_health: 88,
      temporal_stability_health: 22,
      spatial_consistency_health: 44,
    };
  } else if (stationId === 'AWS_019') {
    healthIndex = 61;
    status = 'ATTENTION';
    trend = 'DEGRADING';
    recommendation = 'PRIORITY_INSPECTION';
    scores = {
      anomaly_health: 70,
      data_quality_health: 55,
      communication_health: 48,
      temporal_stability_health: 80,
      spatial_consistency_health: 75,
    };
  }

  // 30-day health history
  const history: Array<{ timestamp: string; score: number }> = [];
  const baseTime = new Date('2026-09-17T13:00:00Z').getTime();
  for (let d = 29; d >= 0; d--) {
    const t = new Date(baseTime - d * 24 * 3600 * 1000).toISOString().split('T')[0];
    const noise = Math.sin(d / 4) * 2;
    const dayScore = Math.max(20, Math.min(100, Math.round(healthIndex + noise - (30 - d) * 0.1)));
    history.push({ timestamp: t, score: dayScore });
  }

  return {
    station_id: stationId,
    station_name: station.station_name,
    timestamp: '2026-09-17T13:05:00Z',
    health_index: healthIndex,
    health_status: status,
    health_trend: trend,
    maintenance_recommendation: recommendation,
    component_scores: scores,
    parameter_health: {
      temperature_c: {
        score: stationId === 'AWS_014' ? 38 : stationId === '42182099999' ? 78 : 96,
        status: stationId === 'AWS_014' ? 'DEGRADED' : 'HEALTHY',
        trend: stationId === 'AWS_014' ? 'DEGRADING' : 'STABLE',
      },
      humidity_pct: {
        score: 92,
        status: 'HEALTHY',
        trend: 'STABLE',
      },
      pressure_hpa: {
        score: stationId === 'AWS_007' ? 64 : 95,
        status: stationId === 'AWS_007' ? 'ATTENTION' : 'HEALTHY',
        trend: stationId === 'AWS_007' ? 'DEGRADING' : 'STABLE',
      },
    },
    history,
  };
}
