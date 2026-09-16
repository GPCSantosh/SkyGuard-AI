import { useQuery } from '@tanstack/react-query';
import {
  fetchAnomalies,
  fetchAnomalyDetail,
  fetchAnomalyExplanation,
} from '../api/anomalies';

export function useAnomalies(params?: {
  stationId?: string;
  decision?: string;
  severity?: string;
  startTime?: string;
  endTime?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['anomalies', params],
    queryFn: () => fetchAnomalies(params),
    refetchInterval: 5000,
  });
}

export function useAnomalyDetail(eventId: string) {
  return useQuery({
    queryKey: ['anomaly', eventId],
    queryFn: () => fetchAnomalyDetail(eventId),
    enabled: Boolean(eventId),
  });
}

export function useAnomalyExplanation(eventId: string) {
  return useQuery({
    queryKey: ['anomaly', eventId, 'explanation'],
    queryFn: () => fetchAnomalyExplanation(eventId),
    enabled: Boolean(eventId),
  });
}
