/**
 * SkyGuard AI — Stations API Service
 * Authoritative backend endpoints:
 * - GET /api/v1/stations
 * - GET /api/v1/stations/{station_id}
 * - GET /api/v1/stations/{station_id}/latest
 * - GET /api/v1/stations/{station_id}/history
 */

import { apiClient, USE_MOCK_DATA } from './client';
import { Station, LiveStationSnapshot, WeatherObservation, PaginatedResponse } from '../types/api';
import { MOCK_STATIONS } from '../mock/mockStations';
import { generateStationHistory } from '../mock/mockObservations';

export const stationsApi = {
  async getStations(): Promise<Station[]> {
    if (USE_MOCK_DATA) {
      return [...MOCK_STATIONS];
    }
    return apiClient.get<Station[]>('/stations');
  },

  async getStation(stationId: string): Promise<Station> {
    if (USE_MOCK_DATA) {
      const station = MOCK_STATIONS.find((s) => s.station_id === stationId);
      if (!station) throw new Error(`Station ${stationId} not found`);
      return { ...station };
    }
    return apiClient.get<Station>(`/stations/${stationId}`);
  },

  async getStationLatest(stationId: string): Promise<LiveStationSnapshot> {
    if (USE_MOCK_DATA) {
      const station = MOCK_STATIONS.find((s) => s.station_id === stationId) || MOCK_STATIONS[0];
      return {
        station_id: station.station_id,
        station_name: station.station_name,
        timestamp: station.last_seen_timestamp || new Date().toISOString(),
        status: station.status,
        latest_observation: station.latest_observation!,
        health_index: station.health_index || 90,
        health_status: station.health_status || 'HEALTHY',
        recent_anomalies: [],
        freshness_seconds: station.latest_observation?.freshness_seconds || 15,
      };
    }
    return apiClient.get<LiveStationSnapshot>(`/stations/${stationId}/latest`);
  },

  async getStationHistory(
    stationId: string,
    window: '6h' | '24h' | '7d' | '30d' = '24h',
    params?: { start_time?: string; end_time?: string; limit?: number; offset?: number }
  ): Promise<WeatherObservation[]> {
    if (USE_MOCK_DATA) {
      return generateStationHistory(stationId, window);
    }
    const query = new URLSearchParams();
    if (params?.start_time) query.set('start_time', params.start_time);
    if (params?.end_time) query.set('end_time', params.end_time);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));

    const res = await apiClient.get<PaginatedResponse<WeatherObservation>>(
      `/stations/${stationId}/history?${query.toString()}`
    );
    return res.items;
  },
};
