/**
 * TypeScript Data Models for SkyGuard AI Meteorological Operations UI
 */

export type ObservationSource =
  | 'HISTORICAL_CSV'
  | 'SIMULATOR'
  | 'WEATHER_API'
  | 'MQTT'
  | 'MANUAL_INJECTION';

export interface WeatherObservation {
  station_id: string;
  timestamp: string; // ISO-8601 UTC
  temperature?: number | null; // °C
  pressure?: number | null; // hPa
  humidity?: number | null; // %
  latitude: number;
  longitude: number;
  elevation?: number | null;
  source: ObservationSource;
  ingestion_timestamp: string;
  metadata?: Record<string, unknown>;
}

export type AnomalyCategory =
  | 'NORMAL'
  | 'SPIKE'
  | 'SMALL_SPIKE'
  | 'DRIFT'
  | 'OFFSET'
  | 'FROZEN_SENSOR'
  | 'INTERMITTENT_SENSOR'
  | 'MISSING_DATA'
  | 'COMMUNICATION_ERROR'
  | 'DUPLICATE_DATA'
  | 'OUT_OF_ORDER_DATA'
  | 'MULTIVARIATE_INCONSISTENCY'
  | 'POSSIBLE_GENUINE_EVENT'
  | 'UNCERTAIN'
  | 'MULTI_FAULT';

export type AnomalySeverity = 'NOMINAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface AnomalyRecord {
  anomaly_id?: string;
  station_id: string;
  timestamp: string;
  parameter: 'temperature' | 'pressure' | 'humidity' | 'multivariate';
  category: AnomalyCategory;
  severity: AnomalySeverity;
  anomaly_score: number;
  confidence: number;
  is_spatial_corroborated: boolean;
  contributing_features: string[];
  explanation?: string;
  model_version: string;
  created_at: string;
}

export type HealthTier = 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'OFFLINE';

export interface SensorHealthStatus {
  station_id: string;
  timestamp: string;
  overall_health_score: number; // 0 to 100
  health_tier: HealthTier;
  temperature_health?: number | null;
  pressure_health?: number | null;
  humidity_health?: number | null;
  anomaly_count_24h: number;
  missing_intervals_24h: number;
  data_completeness_pct_24h: number;
  drift_detected: boolean;
  frozen_detected: boolean;
}

export interface StationMetadata {
  station_id: string;
  name: string;
  latitude: number;
  longitude: number;
  elevation?: number | null;
  state?: string | null;
  sampling_interval_seconds: number;
  status: 'ACTIVE' | 'DEGRADED' | 'MAINTENANCE' | 'OFFLINE' | 'DECOMMISSIONED';
  installed_sensors: string[];
}
