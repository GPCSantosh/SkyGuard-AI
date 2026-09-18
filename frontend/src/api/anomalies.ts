/**
 * SkyGuard AI — Anomalies & Explainability API Service
 * Authoritative endpoints:
 * - GET /api/v1/anomalies
 * - GET /api/v1/anomalies/{event_id}
 * - GET /api/v1/anomalies/{event_id}/explanation
 */

import { apiClient, USE_MOCK_DATA } from './client';
import { AnomalyEventRecord, ExplanationSummary, PaginatedResponse } from '../types/api';
import { MOCK_ANOMALIES, getMockAnomalyExplanation } from '../mock/mockAnomalies';

export interface AnomalyFilterParams {
  station_id?: string;
  decision?: string;
  severity?: string;
  start_time?: string;
  end_time?: string;
  limit?: number;
  offset?: number;
}

export const anomaliesApi = {
  async getAnomalies(params?: AnomalyFilterParams): Promise<AnomalyEventRecord[]> {
    if (USE_MOCK_DATA) {
      let list = [...MOCK_ANOMALIES];
      if (params?.station_id) {
        list = list.filter((a) => a.station_id === params.station_id);
      }
      if (params?.decision) {
        list = list.filter((a) => a.decision === params.decision);
      }
      if (params?.severity) {
        list = list.filter((a) => a.severity === params.severity);
      }
      return list;
    }

    const query = new URLSearchParams();
    if (params?.station_id) query.set('station_id', params.station_id);
    if (params?.decision) query.set('decision', params.decision);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.start_time) query.set('start_time', params.start_time);
    if (params?.end_time) query.set('end_time', params.end_time);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));

    const res = await apiClient.get<PaginatedResponse<AnomalyEventRecord>>(
      `/anomalies?${query.toString()}`
    );
    return res.items;
  },

  async getAnomaly(eventId: string): Promise<AnomalyEventRecord> {
    if (USE_MOCK_DATA) {
      const anom = MOCK_ANOMALIES.find((a) => a.event_id === eventId);
      if (!anom) throw new Error(`Anomaly event ${eventId} not found`);
      return { ...anom };
    }
    return apiClient.get<AnomalyEventRecord>(`/anomalies/${eventId}`);
  },

  async getAnomalyExplanation(eventId: string): Promise<ExplanationSummary> {
    if (USE_MOCK_DATA) {
      return getMockAnomalyExplanation(eventId);
    }
    return apiClient.get<ExplanationSummary>(`/anomalies/${eventId}/explanation`);
  },
};
