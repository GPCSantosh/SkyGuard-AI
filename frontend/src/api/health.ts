/**
 * SkyGuard AI — Sensor Health API Service
 * Authoritative endpoint:
 * - GET /api/v1/stations/{station_id}/health
 */

import { apiClient, USE_MOCK_DATA } from './client';
import { SensorHealthSummary } from '../types/api';
import { getMockStationHealth } from '../mock/mockHealth';
import { MOCK_STATIONS } from '../mock/mockStations';

export const healthApi = {
  async getStationHealth(stationId: string): Promise<SensorHealthSummary> {
    if (USE_MOCK_DATA) {
      return getMockStationHealth(stationId);
    }
    return apiClient.get<SensorHealthSummary>(`/stations/${stationId}/health`);
  },

  async getAllStationsHealth(): Promise<SensorHealthSummary[]> {
    if (USE_MOCK_DATA) {
      return MOCK_STATIONS.map((s) => getMockStationHealth(s.station_id));
    }
    // Aggregate queries for all monitored stations
    const stations = await apiClient.get<Array<{ station_id: string }>>('/stations');
    const promises = stations.map((s) =>
      apiClient.get<SensorHealthSummary>(`/stations/${s.station_id}/health`).catch(() => null)
    );
    const results = await Promise.all(promises);
    return results.filter((r): r is SensorHealthSummary => r !== null);
  },
};
