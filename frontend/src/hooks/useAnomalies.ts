/**
 * SkyGuard AI — TanStack Query Hooks for Anomalies & Explainability
 */

import { useQuery } from '@tanstack/react-query';
import { anomaliesApi, AnomalyFilterParams } from '../api/anomalies';

export function useAnomalies(params?: AnomalyFilterParams) {
  return useQuery({
    queryKey: ['anomalies', params],
    queryFn: () => anomaliesApi.getAnomalies(params),
    refetchInterval: 15000,
    staleTime: 10000,
  });
}

export function useAnomaly(eventId: string) {
  return useQuery({
    queryKey: ['anomaly', eventId],
    queryFn: () => anomaliesApi.getAnomaly(eventId),
    enabled: Boolean(eventId),
    staleTime: 30000,
  });
}

export function useAnomalyExplanation(eventId: string) {
  return useQuery({
    queryKey: ['anomaly', eventId, 'explanation'],
    queryFn: () => anomaliesApi.getAnomalyExplanation(eventId),
    enabled: Boolean(eventId),
    staleTime: 60000,
  });
}
