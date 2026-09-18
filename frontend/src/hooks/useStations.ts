/**
 * SkyGuard AI — TanStack Query Hooks for Stations Telemetry
 */

import { useQuery } from '@tanstack/react-query';
import { stationsApi } from '../api/stations';

export function useStations() {
  return useQuery({
    queryKey: ['stations'],
    queryFn: () => stationsApi.getStations(),
    refetchInterval: 15000, // 15s background polling fallback
    staleTime: 10000,
  });
}

export function useStation(stationId: string) {
  return useQuery({
    queryKey: ['station', stationId],
    queryFn: () => stationsApi.getStation(stationId),
    enabled: Boolean(stationId),
    staleTime: 15000,
  });
}

export function useStationLatest(stationId: string) {
  return useQuery({
    queryKey: ['station', stationId, 'latest'],
    queryFn: () => stationsApi.getStationLatest(stationId),
    enabled: Boolean(stationId),
    refetchInterval: 15000,
    staleTime: 8000,
  });
}

export function useStationHistory(
  stationId: string,
  window: '6h' | '24h' | '7d' | '30d' = '24h'
) {
  return useQuery({
    queryKey: ['station', stationId, 'history', window],
    queryFn: () => stationsApi.getStationHistory(stationId, window),
    enabled: Boolean(stationId),
    refetchInterval: 30000,
    staleTime: 20000,
  });
}
