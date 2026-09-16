import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchSystemHealth, fetchReplayStatus, stepReplaySimulation } from '../api/system';

export function useSystemHealth() {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: fetchSystemHealth,
    refetchInterval: 5000,
  });
}

export function useReplayStatus() {
  return useQuery({
    queryKey: ['replay', 'status'],
    queryFn: fetchReplayStatus,
    refetchInterval: 3000,
  });
}

export function useStepReplay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (count: number = 1) => stepReplaySimulation(count),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stations'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      queryClient.invalidateQueries({ queryKey: ['corrections'] });
      queryClient.invalidateQueries({ queryKey: ['system'] });
      queryClient.invalidateQueries({ queryKey: ['replay'] });
    },
  });
}
