import { useQuery } from '@tanstack/react-query';
import { fetchCorrections, fetchCorrectionDetail } from '../api/corrections';

export function useCorrections(params?: {
  stationId?: string;
  status?: string;
  targetVariable?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['corrections', params],
    queryFn: () => fetchCorrections(params),
    refetchInterval: 8000,
  });
}

export function useCorrectionDetail(observationId: string) {
  return useQuery({
    queryKey: ['correction', observationId],
    queryFn: () => fetchCorrectionDetail(observationId),
    enabled: Boolean(observationId),
  });
}
