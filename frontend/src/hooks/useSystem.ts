import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchSystemHealth,
  fetchReplayStatus,
  fetchReplayScenarios,
  loadReplayScenario,
  resetReplaySimulation,
  stepReplaySimulation,
  fetchLiveSourceHealth,
  triggerLivePoll,
} from '../api/system';

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
    refetchInterval: 2000,
  });
}

export function useReplayScenarios() {
  return useQuery({
    queryKey: ['replay', 'scenarios'],
    queryFn: fetchReplayScenarios,
    staleTime: 60000,
  });
}

export function useLoadScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scenarioId: string) => loadReplayScenario(scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['replay'] });
      queryClient.invalidateQueries({ queryKey: ['stations'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      queryClient.invalidateQueries({ queryKey: ['corrections'] });
    },
  });
}

export function useResetReplay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetReplaySimulation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['replay'] });
      queryClient.invalidateQueries({ queryKey: ['stations'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      queryClient.invalidateQueries({ queryKey: ['corrections'] });
      queryClient.invalidateQueries({ queryKey: ['system'] });
    },
  });
}

export function useLiveSourceHealth() {
  return useQuery({
    queryKey: ['live', 'source-health'],
    queryFn: fetchLiveSourceHealth,
    refetchInterval: 5000,
  });
}

export function useTriggerLivePoll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: triggerLivePoll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['live', 'source-health'] });
      queryClient.invalidateQueries({ queryKey: ['stations'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      queryClient.invalidateQueries({ queryKey: ['system'] });
    },
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
