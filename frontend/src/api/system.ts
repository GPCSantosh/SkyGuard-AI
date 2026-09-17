import { apiClient } from './client';
import {
  SystemHealthStatus,
  ReplayStatus,
  ReplayScenario,
  LiveSourceHealthSummary,
} from '../types/api';

export async function fetchSystemHealth(): Promise<SystemHealthStatus> {
  return apiClient<SystemHealthStatus>('/system/health');
}

export async function fetchReplayStatus(): Promise<ReplayStatus> {
  return apiClient<ReplayStatus>('/replay/status');
}

export async function fetchReplayScenarios(): Promise<ReplayScenario[]> {
  return apiClient<ReplayScenario[]>('/replay/scenarios');
}

export async function loadReplayScenario(scenarioId: string): Promise<{
  status: string;
  loaded_scenario_id: string;
  total_observations: number;
  current_index: number;
}> {
  return apiClient('/replay/load-scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
}

export async function resetReplaySimulation(): Promise<{
  status: string;
  current_index: number;
  emitted_count: number;
  current_scenario_id: string;
  database_preserved: boolean;
}> {
  return apiClient('/replay/reset', {
    method: 'POST',
  });
}

export async function stepReplaySimulation(count: number = 1): Promise<{
  mode: string;
  steps_executed: number;
  current_index: number;
  total_emitted: number;
  results_summary: Array<{
    station_id: string;
    timestamp: string;
    status: string;
    decision: string | null;
    event_id: string | null;
  }>;
}> {
  return apiClient(`/replay/step?count=${count}`, {
    method: 'POST',
  });
}

export async function fetchLiveSourceHealth(): Promise<LiveSourceHealthSummary> {
  return apiClient<LiveSourceHealthSummary>('/live/source-health');
}

export async function triggerLivePoll(): Promise<{
  status: string;
  stations_polled: number;
  observations_ingested: number;
  poll_duration_ms?: number;
  source_state: string;
}> {
  return apiClient('/live/poll-now', {
    method: 'POST',
  });
}
