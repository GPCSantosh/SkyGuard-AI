/**
 * SkyGuard AI — TanStack Query Hooks for Advisory Corrections Review
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { correctionsApi, CorrectionFilterParams } from '../api/corrections';

export function useCorrections(params?: CorrectionFilterParams) {
  return useQuery({
    queryKey: ['corrections', params],
    queryFn: () => correctionsApi.getCorrections(params),
    refetchInterval: 15000,
    staleTime: 10000,
  });
}

export function useCorrection(observationId: string) {
  return useQuery({
    queryKey: ['correction', observationId],
    queryFn: () => correctionsApi.getCorrection(observationId),
    enabled: Boolean(observationId),
    staleTime: 30000,
  });
}

export function useReviewCorrection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      observationId,
      action,
      note,
    }: {
      observationId: string;
      action: 'ACCEPT' | 'REJECT' | 'FLAG';
      note?: string;
    }) => correctionsApi.reviewCorrection(observationId, action, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['corrections'] });
    },
  });
}
