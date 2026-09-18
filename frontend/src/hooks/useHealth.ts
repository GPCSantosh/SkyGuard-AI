/**
 * SkyGuard AI — TanStack Query Hooks for Sensor Health Indexing
 */

import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../api/health';

export function useStationHealth(stationId: string) {
  return useQuery({
    queryKey: ['health', stationId],
    queryFn: () => healthApi.getStationHealth(stationId),
    enabled: Boolean(stationId),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useAllStationsHealth() {
  return useQuery({
    queryKey: ['health', 'all'],
    queryFn: () => healthApi.getAllStationsHealth(),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}
