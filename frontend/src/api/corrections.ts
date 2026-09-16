import { apiClient } from './client';
import { CorrectionRecommendation, PaginatedResponse } from '../types/api';

export async function fetchCorrections(params?: {
  stationId?: string;
  status?: string;
  targetVariable?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<CorrectionRecommendation>> {
  const query = new URLSearchParams();
  if (params?.stationId) query.set('station_id', params.stationId);
  if (params?.status) query.set('status', params.status);
  if (params?.targetVariable) query.set('target_variable', params.targetVariable);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));

  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiClient<PaginatedResponse<CorrectionRecommendation>>(`/corrections${qs}`);
}

export async function fetchCorrectionDetail(observationId: string): Promise<CorrectionRecommendation> {
  return apiClient<CorrectionRecommendation>(`/corrections/${observationId}`);
}
