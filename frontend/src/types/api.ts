/**
 * Strict TypeScript Data Models for SkyGuard AI
 * Directly aligned with FastAPI / Pydantic schemas in backend/app/models/
 */

export type HybridDecisionType =
  | 'NORMAL'
  | 'POSSIBLE_GENUINE_EVENT'
  | 'PROBABLE_SENSOR_ANOMALY'
  | 'PROBABLE_DATA_QUALITY_ISSUE'
  | 'UNCERTAIN';

export type AlertSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type HealthStatusBand = 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'OFFLINE';

export type StationOperationalStatus = 'ACTIVE' | 'DEGRADED' | 'MAINTENANCE' | 'OFFLINE' | 'DECOMMISSIONED';

export type RecommendationStatus =
  | 'NO_CORRECTION_RECOMMENDED'
  | 'REVIEW_RECOMMENDED'
  | 'CORRECTION_CANDIDATE'
  | 'INSUFFICIENT_EVIDENCE';

export type EstimationMethod =
  | 'CAUSAL_TEMPORAL_INTERPOLATION'
  | 'RETROSPECTIVE_INTERPOLATION'
  | 'SPATIAL_IDW_CONSENSUS'
  | 'NEIGHBOR_WEIGHTED_MEDIAN'
  | 'ROLLING_BASELINE'
  | 'COMBINED_TEMPORAL_SPATIAL'
  | 'NO_ESTIMATE';

export type MethodQuality = 'HIGH' | 'MEDIUM' | 'LOW' | 'POOR';

export interface WeatherObservation {
  station_id: string;
  timestamp: string; // ISO 8601 UTC
  temperature?: number | null; // °C
  pressure?: number | null; // hPa
  humidity?: number | null; // %
  latitude: number;
  longitude: number;
  elevation?: number | null;
  source: string;
  ingestion_timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface LiveStationSnapshot {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  status: StationOperationalStatus;
  last_seen_timestamp?: string | null;
  latest_temperature_c?: number | null;
  latest_humidity_pct?: number | null;
  latest_pressure_hpa?: number | null;
  latest_decision: HybridDecisionType;
  latest_health_score?: number | null;
  latest_health_band: HealthStatusBand;
  active_anomaly_count_24h: number;
}

export interface StationItem {
  station_id: string;
  name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  state?: string | null;
  status: StationOperationalStatus;
  sampling_interval_seconds: number;
  latest_snapshot?: LiveStationSnapshot | null;
}

export interface AnomalyEventRecord {
  event_id: string;
  station_id: string;
  timestamp: string;
  decision: HybridDecisionType;
  severity: AlertSeverity;
  reason_codes: string[];
  observed_values: Record<string, number | null>;
  recommended_values: Record<string, number | null>;
  explanation_summary: string;
  created_at: string;
}

export interface FeatureContribution {
  feature_name: string;
  feature_value: number | string | null;
  contribution?: number;
  contribution_score?: number; // SHAP value or proxy
  direction: 'increases_anomaly' | 'decreases_anomaly' | 'neutral' | 'INCREASES_ANOMALY' | 'DECREASES_ANOMALY' | 'NEUTRAL';
  rank?: number;
  description?: string;
}

export interface NeighborContextRecord {
  neighbor_station_id: string;
  distance_km: number;
  observed_value?: number | null;
  delta?: number | null;
  is_consistent: boolean;
}

export interface NeighborComparisonData {
  target_station_id: string;
  target_observed_value?: number | null;
  neighbors: NeighborContextRecord[];
}

export interface ExplanationSummary {
  event_id?: string;
  station_id: string;
  timestamp: string;
  decision: HybridDecisionType;
  severity: AlertSeverity;
  summary?: string;
  operator_summary?: string;
  confidence_score?: number;
  is_degraded_mode?: boolean;
  reason_codes?: string[];
  evidence_hierarchy?: {
    direct_evidence?: unknown;
    model_evidence?: unknown;
    contextual_evidence?: unknown;
    operational_interpretation?: unknown;
  };
  feature_contributions?: FeatureContribution[];
  model_contributions?: FeatureContribution[];
  neighbor_comparison?: NeighborComparisonData | null;
  neighbor_comparisons?: NeighborContextRecord[];
  recommended_investigation_steps?: string[];
  recommended_actions?: string[];
  created_at?: string;
}

export interface HealthComponentScores {
  anomaly_score: number; // 0-100
  data_quality_score: number; // 0-100
  communication_score: number; // 0-100
  temporal_stability_score: number; // 0-100
  spatial_consistency_score: number; // 0-100
}

export interface ParameterHealthScores {
  temperature_health?: number | null;
  humidity_health?: number | null;
  pressure_health?: number | null;
}

export interface SensorHealthSummary {
  station_id: string;
  timestamp: string;
  overall_health_score: number; // 0-100
  status_band: HealthStatusBand;
  trend: 'IMPROVING' | 'STABLE' | 'DEGRADING';
  components: HealthComponentScores;
  parameter_health: ParameterHealthScores;
  anomaly_count_24h: number;
  missing_intervals_24h: number;
  data_completeness_pct_24h: number;
  maintenance_recommendation: string;
  evaluated_at: string;
}

export interface UncertaintyEstimate {
  estimate_range: [number, number];
  standard_error?: number | null;
  absolute_deviation?: number | null;
  supporting_neighbor_count: number;
  method_quality: MethodQuality;
  confidence_index: number;
  notes: string[];
}

export interface CorrectionRecommendation {
  observation_id: string;
  station_id: string;
  timestamp: string;
  target_variable: string;
  observed_value: number;
  recommended_value?: number | null;
  status: RecommendationStatus;
  method: EstimationMethod;
  decision_type: HybridDecisionType | string;
  reason_codes: string[];
  supporting_evidence: string[];
  uncertainty?: UncertaintyEstimate | null;
  multivariate_consistent: boolean;
  station_health_score?: number | null;
  station_health_band?: string | null;
  operator_summary: string;
  audit_metadata?: {
    imputation_engine_version: string;
    decision_engine_version: string;
    is_causal_mode: boolean;
    generated_at: string;
  };
  created_at: string;
}

export interface SystemHealthStatus {
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
  service: string;
  version: string;
  database_status: string;
  model_registry_status: string;
  active_model_id: string;
  spatial_topology_stations_count: number;
  active_monitored_stations: number;
  total_observations_processed: number;
  last_processed_timestamp?: string | null;
  mean_pipeline_latency_ms: number;
  replay_simulator_status: string;
  uptime_seconds: number;
  checked_at: string;
}

export interface ReplayStatus {
  is_running: boolean;
  total_queued_observations: number;
  emitted_count: number;
  speed_multiplier: number;
  registered_injected_anomalies_count: number;
}

export interface PaginationMeta {
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}
