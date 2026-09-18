/**
 * SkyGuard AI — Advisory Correction Recommendations API Service
 * Authoritative endpoints:
 * - GET /api/v1/corrections
 * - GET /api/v1/corrections/{observation_id}
 */

import { apiClient, USE_MOCK_DATA } from './client';
import { CorrectionRecommendation, PaginatedResponse } from '../types/api';
import { MOCK_CORRECTIONS } from '../mock/mockCorrections';

export interface CorrectionFilterParams {
  station_id?: string;
  status?: string;
  target_variable?: string;
  limit?: number;
  offset?: number;
}

export const correctionsApi = {
  async getCorrections(params?: CorrectionFilterParams): Promise<CorrectionRecommendation[]> {
    if (USE_MOCK_DATA) {
      let list = [...MOCK_CORRECTIONS];
      if (params?.station_id) {
        list = list.filter((c) => c.station_id === params.station_id);
      }
      if (params?.status && params.status !== 'ALL') {
        list = list.filter((c) => c.status === params.status);
      }
      if (params?.target_variable) {
        list = list.filter((c) => c.target_variable === params.target_variable);
      }
      return list;
    }

    const query = new URLSearchParams();
    if (params?.station_id) query.set('station_id', params.station_id);
    if (params?.status && params.status !== 'ALL') query.set('status', params.status);
    if (params?.target_variable) query.set('target_variable', params.target_variable);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));

    const res = await apiClient.get<PaginatedResponse<CorrectionRecommendation>>(
      `/corrections?${query.toString()}`
    );
    return res.items;
  },

  async getCorrection(observationId: string): Promise<CorrectionRecommendation> {
    if (USE_MOCK_DATA) {
      const item = MOCK_CORRECTIONS.find((c) => c.observation_id === observationId);
      if (!item) throw new Error(`Correction ${observationId} not found`);
      return { ...item };
    }
    return apiClient.get<CorrectionRecommendation>(`/corrections/${observationId}`);
  },

  async reviewCorrection(
    observationId: string,
    action: 'ACCEPT' | 'REJECT' | 'FLAG',
    _note?: string
  ): Promise<{ status: string; message: string }> {
    if (USE_MOCK_DATA) {
      const item = MOCK_CORRECTIONS.find((c) => c.observation_id === observationId);
      if (item) {
        if (action === 'ACCEPT') item.status = 'ACCEPTED';
        if (action === 'REJECT') item.status = 'REJECTED';
        if (action === 'FLAG') item.status = 'REVIEW_REQUIRED';
      }
      return {
        status: 'SUCCESS',
        message: `Recommendation ${observationId} acknowledged as ${action}. Raw telemetry preserved.`,
      };
    }

    return apiClient.post<{ status: string; message: string }>(
      `/corrections/${observationId}/review`,
      { action, note: _note }
    );
  },
};
