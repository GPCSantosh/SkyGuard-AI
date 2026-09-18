/**
 * SkyGuard AI — System Diagnostics & Subsystems API Service
 * Authoritative endpoints:
 * - GET /api/v1/system/health
 * - GET /api/v1/live/status
 * - POST /api/v1/live/poll-now
 */

import { apiClient, USE_MOCK_DATA } from './client';
import { SystemHealthStatus } from '../types/api';
import { MOCK_SYSTEM_HEALTH } from '../mock/mockSystem';

export const systemApi = {
  async getSystemHealth(): Promise<SystemHealthStatus> {
    if (USE_MOCK_DATA) {
      return { ...MOCK_SYSTEM_HEALTH };
    }
    return apiClient.get<SystemHealthStatus>('/system/health');
  },

  async getLiveStatus(): Promise<{ status: string; operational_mode: string; active_source: string }> {
    if (USE_MOCK_DATA) {
      return {
        status: 'OPERATIONAL',
        operational_mode: 'DEMO / SYNTHETIC VALIDATION',
        active_source: 'SYNTHETIC_REPLAY_ENGINE',
      };
    }
    return apiClient.get<{ status: string; operational_mode: string; active_source: string }>(
      '/live/status'
    );
  },

  async triggerImmediatePoll(): Promise<{ status: string; stations_polled: number }> {
    if (USE_MOCK_DATA) {
      return { status: 'OK', stations_polled: 8 };
    }
    return apiClient.post<{ status: string; stations_polled: number }>('/live/poll-now');
  },
};
