/**
 * SkyGuard AI — WebSocket Event Protocol Types (RFC 6455)
 * Strict discriminated union for stream events matching WEBSOCKET_PROTOCOL.md
 */

import {
  HybridDecisionType,
  DecisionSeverity,
  WeatherObservation,
  StationStatusType,
} from './api';

export type EventType =
  | 'observation.updated'
  | 'anomaly.created'
  | 'health.updated'
  | 'correction.created'
  | 'station.status_changed'
  | 'system.status_changed';

export interface ObservationUpdatedPayload {
  station_id: string;
  station_name?: string;
  timestamp: string;
  temperature: number | null;
  humidity: number | null;
  pressure: number | null;
  dew_point_c?: number | null;
  data_quality_status: string;
  freshness_seconds: number;
}

export interface AnomalyCreatedPayload {
  event_id: string;
  station_id: string;
  station_name?: string;
  timestamp: string;
  decision: HybridDecisionType;
  severity: DecisionSeverity;
  summary: string;
  reason_codes: string[];
  observed_values: Record<string, number | null>;
  recommended_values?: Record<string, number | null>;
}

export interface HealthUpdatedPayload {
  station_id: string;
  timestamp: string;
  health_index: number;
  health_status: string;
  health_trend: string;
  maintenance_recommendation: string;
  parameter_health?: Record<string, number>;
  component_scores?: {
    anomaly_health: number;
    data_quality_health: number;
    communication_health: number;
    temporal_stability_health: number;
    spatial_consistency_health: number;
  };
}

export interface CorrectionCreatedPayload {
  observation_id: string;
  station_id: string;
  timestamp: string;
  target_variable: string;
  observed_value: number;
  recommended_value: number | null;
  confidence_lower?: number;
  confidence_upper?: number;
  status: string;
  method: string;
}

export interface StationStatusChangedPayload {
  station_id: string;
  previous_status: StationStatusType;
  current_status: StationStatusType;
  timestamp: string;
  reason?: string;
}

export interface SystemStatusChangedPayload {
  component: string;
  status: 'CONNECTED' | 'DISCONNECTED' | 'OK' | 'WARN' | 'ERROR';
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface BaseEnvelope {
  event_id: string;
  timestamp: string;
  station_id: string | null;
  schema_version: '1.0';
}

export interface ObservationUpdatedEnvelope extends BaseEnvelope {
  event_type: 'observation.updated';
  payload: ObservationUpdatedPayload;
}

export interface AnomalyCreatedEnvelope extends BaseEnvelope {
  event_type: 'anomaly.created';
  payload: AnomalyCreatedPayload;
}

export interface HealthUpdatedEnvelope extends BaseEnvelope {
  event_type: 'health.updated';
  payload: HealthUpdatedPayload;
}

export interface CorrectionCreatedEnvelope extends BaseEnvelope {
  event_type: 'correction.created';
  payload: CorrectionCreatedPayload;
}

export interface StationStatusChangedEnvelope extends BaseEnvelope {
  event_type: 'station.status_changed';
  payload: StationStatusChangedPayload;
}

export interface SystemStatusChangedEnvelope extends BaseEnvelope {
  event_type: 'system.status_changed';
  payload: SystemStatusChangedPayload;
}

export type WebSocketEnvelope =
  | ObservationUpdatedEnvelope
  | AnomalyCreatedEnvelope
  | HealthUpdatedEnvelope
  | CorrectionCreatedEnvelope
  | StationStatusChangedEnvelope
  | SystemStatusChangedEnvelope;

export type ConnectionState =
  | 'CONNECTED'
  | 'CONNECTING'
  | 'RECONNECTING'
  | 'ERROR'
  | 'DISCONNECTED'
  | 'POLLING';
