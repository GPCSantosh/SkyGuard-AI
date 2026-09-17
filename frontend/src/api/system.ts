import { apiClient } from './client';
import { SystemHealthStatus, ReplayStatus, LiveSourceHealthSummary } from '../types/api';

export async function fetchSystemHealth(): Promise<SystemHealthStatus> {
  return apiClient<SystemHealthStatus>('/system/health');
}

export async function fetchReplayStatus(): Promise<ReplayStatus> {
  return apiClient<ReplayStatus>('/replay/status');
}

export async function stepReplaySimulation(count: number = 1): Promise<{
  steps_executed: number;
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
