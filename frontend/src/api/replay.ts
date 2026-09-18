/**
 * SkyGuard AI — Stream Replay Simulation API Service
 * Authoritative endpoints:
 * - GET /api/v1/replay/status
 * - POST /api/v1/replay/step?count={n}
 * - POST /api/v1/replay/reset
 */

import { apiClient, USE_MOCK_DATA } from './client';
import { ReplayStatus } from '../types/api';
import { MOCK_REPLAY_STATUS } from '../mock/mockSystem';

export const replayApi = {
  async getReplayStatus(): Promise<ReplayStatus> {
    if (USE_MOCK_DATA) {
      return { ...MOCK_REPLAY_STATUS };
    }
    return apiClient.get<ReplayStatus>('/replay/status');
  },

  async stepReplay(count = 1): Promise<ReplayStatus> {
    if (USE_MOCK_DATA) {
      MOCK_REPLAY_STATUS.current_step += count;
      MOCK_REPLAY_STATUS.emitted_packets += count;
      MOCK_REPLAY_STATUS.queued_packets = Math.max(0, MOCK_REPLAY_STATUS.queued_packets - count);
      return { ...MOCK_REPLAY_STATUS };
    }
    const res = await apiClient.post<ReplayStatus>(`/replay/step?count=${count}`);
    return res;
  },

  async resetReplay(): Promise<ReplayStatus> {
    if (USE_MOCK_DATA) {
      MOCK_REPLAY_STATUS.current_step = 0;
      MOCK_REPLAY_STATUS.emitted_packets = 0;
      MOCK_REPLAY_STATUS.queued_packets = 240;
      return { ...MOCK_REPLAY_STATUS };
    }
    return apiClient.post<ReplayStatus>('/replay/reset');
  },
};
