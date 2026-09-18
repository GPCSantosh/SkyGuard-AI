/**
 * SkyGuard AI — TanStack Query Hooks for System Observability & Replay Engine
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { systemApi } from '../api/system';
import { replayApi } from '../api/replay';

export function useSystemHealth() {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: () => systemApi.getSystemHealth(),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useLiveStatus() {
  return useQuery({
    queryKey: ['system', 'live-status'],
    queryFn: () => systemApi.getLiveStatus(),
    refetchInterval: 15000,
    staleTime: 10000,
  });
}

export function useReplayStatus() {
  return useQuery({
    queryKey: ['replay', 'status'],
    queryFn: () => replayApi.getReplayStatus(),
    refetchInterval: 10000,
    staleTime: 5000,
  });
}

export function useReplayActions() {
  const queryClient = useQueryClient();

  const stepMutation = useMutation({
    mutationFn: (count?: number) => replayApi.stepReplay(count),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['replay'] });
      queryClient.invalidateQueries({ queryKey: ['stations'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      queryClient.invalidateQueries({ queryKey: ['corrections'] });
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => replayApi.resetReplay(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['replay'] });
      queryClient.invalidateQueries({ queryKey: ['stations'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      queryClient.invalidateQueries({ queryKey: ['corrections'] });
    },
  });

  const pollNowMutation = useMutation({
    mutationFn: () => systemApi.triggerImmediatePoll(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stations'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
    },
  });

  return {
    step: stepMutation.mutate,
    isStepping: stepMutation.isPending,
    reset: resetMutation.mutate,
    isResetting: resetMutation.isPending,
    pollNow: pollNowMutation.mutate,
    isPollingNow: pollNowMutation.isPending,
  };
}
