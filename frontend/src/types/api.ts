/**
 * SkyGuard AI — TypeScript Domain Contracts
 * Authoritative schemas matching FastAPI models & OpenAPI 3.1 contract.
 */

export type HybridDecisionType =
  | 'NORMAL'
  | 'POSSIBLE_GENUINE_EVENT'
  | 'PROBABLE_SENSOR_ANOMALY'
  | 'PROBABLE_DATA_QUALITY_ISSUE'
  | 'UNCERTAIN';

export type DecisionSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type DecisionReasonCode =
  | 'NOMINAL_OBSERVATION'
  | 'DATA_GAP'
  | 'DUPLICATE_TIMESTAMP'
  | 'OUT_OF_ORDER_TIMESTAMP'
  | 'MISSING_REQUIRED_VARIABLES'
  | 'OUT_OF_RANGE_PHYSICAL'
  | 'PERSISTENT_VALUE'
  | 'RAPID_RATE_OF_CHANGE'
  | 'MULTIVARIATE_DEVIATION'
  | 'ML_HIGH_ANOMALY_SCORE'
  | 'ML_MODERATE_ANOMALY_SCORE'
  | 'LOCAL_SPATIAL_ISOLATION'
  | 'REGIONAL_SPATIAL_AGREEMENT'
  | 'LOCAL_CLUSTER_AGREEMENT'
  | 'INSUFFICIENT_SPATIAL_CONTEXT'
  | 'CONFLICTING_EVIDENCE'
  | 'MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS';

export type StationStatusType = 'ACTIVE' | 'DEGRADED' | 'OFFLINE';

export interface Station {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  elevation_m?: number;
  status: StationStatusType;
  network?: string;
  hardware?: string;
  commissioned_date?: string;
  state?: string;
  district?: string;
  latest_observation?: WeatherObservation;
  health_index?: number;
  health_status?: string;
  active_anomalies_count?: number;
  last_seen_timestamp?: string;
}

export interface WeatherObservation {
  station_id: string;
  station_name?: string;
  timestamp: string; // ISO 8601 UTC
  temperature_c: number | null;
  humidity_pct: number | null;
  pressure_hpa: number | null;
  dew_point_c?: number | null;
  data_quality_status?: 'VALID' | 'WARNING' | 'REJECTED' | 'GAP' | 'DUPLICATE';
  freshness_seconds?: number;

  // Dual-signal & spatial contextual comparator values
  imputed_temperature_c?: number | null;
  imputed_humidity_pct?: number | null;
  imputed_pressure_hpa?: number | null;

  neighbor_median_temperature_c?: number | null;
  neighbor_median_humidity_pct?: number | null;
  neighbor_median_pressure_hpa?: number | null;

  is_anomalous?: boolean;
  anomaly_decision?: HybridDecisionType;
  anomaly_severity?: DecisionSeverity;
}

export interface LiveStationSnapshot {
  station_id: string;
  station_name: string;
  timestamp: string;
  status: StationStatusType;
  latest_observation: WeatherObservation;
  health_index: number;
  health_status: string;
  recent_anomalies: AnomalyEventRecord[];
  freshness_seconds: number;
}

export interface AnomalyEventRecord {
  event_id: string;
  station_id: string;
  station_name?: string;
  timestamp: string;
  decision: HybridDecisionType;
  severity: DecisionSeverity;
  reason_codes: string[];
  observed_values: Record<string, number | null>;
  recommended_values?: Record<string, number | null>;
  expected_values?: Record<string, number | null>;
  explanation_summary: string;
  created_at?: string;
  duration_minutes?: number;
  onset_timestamp?: string;
  peak_timestamp?: string;
  peak_value?: number;
  target_variable?: string;
}

export interface FeatureContribution {
  feature: string;
  display_name?: string;
  value: number;
  contribution: number;
  direction: 'increases_anomaly' | 'decreases_anomaly' | 'neutral';
  description?: string;
}

export interface SpatialEvidence {
  consensus: 'LOCAL_ONLY' | 'LOCAL_CLUSTER' | 'REGIONAL_PATTERN' | 'INSUFFICIENT_CONTEXT';
  neighbor_count: number;
  agreeing_count: number;
  disagreeing_count: number;
  max_deviation?: number;
  neighbors?: Array<{
    station_id: string;
    station_name?: string;
    distance_km: number;
    azimuth_deg?: number;
    temperature_c?: number | null;
    humidity_pct?: number | null;
    pressure_hpa?: number | null;
    status: 'AGREE' | 'DISAGREE' | 'UNKNOWN';
  }>;
}

export interface TemporalEvidence {
  rate_of_change?: number;
  rate_unit?: string;
  flatline_count?: number;
  zscore_1h?: number;
  diurnal_residual?: number;
  is_rate_exceeded?: boolean;
}

export interface DataQualityEvidence {
  quality_status: string;
  missing_fields?: string[];
  communication_gap_minutes?: number | null;
  is_duplicate?: boolean;
  is_out_of_order?: boolean;
  is_physical_out_of_bounds?: boolean;
  evidence_state?: string;
}

export interface MultivariateEvidence {
  is_consistent: boolean;
  thermodynamic_status: string;
  rh_dewpoint_check?: string;
  hypsometric_pressure_check?: string;
}

export interface AuditMetadata {
  model_version?: string;
  feature_version?: string;
  decision_engine_version?: string;
  explanation_engine_version?: string;
  explanation_method?: string;
  input_station_id: string;
  input_timestamp: string;
  generated_at?: string;
}

export interface ExplanationSummary {
  station_id: string;
  timestamp: string;
  decision: HybridDecisionType;
  severity: DecisionSeverity;
  summary: string;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  unavailable_evidence: string[];
  feature_contributions: FeatureContribution[];
  spatial_evidence?: SpatialEvidence;
  temporal_evidence?: TemporalEvidence;
  data_quality_evidence?: DataQualityEvidence;
  multivariate_evidence?: MultivariateEvidence;
  audit_metadata?: AuditMetadata;
  recommended_action?: string;
  anomaly_score?: number;
  calibrated_threshold?: number;
}

export interface ComponentHealthScores {
  anomaly_health: number;
  data_quality_health: number;
  communication_health: number;
  temporal_stability_health: number;
  spatial_consistency_health: number;
}

export interface SensorHealthSummary {
  station_id: string;
  station_name?: string;
  timestamp: string;
  health_index: number;
  health_status: 'HEALTHY' | 'GOOD' | 'ATTENTION' | 'DEGRADED' | 'CRITICAL' | 'INSUFFICIENT_HISTORY';
  health_trend: 'IMPROVING' | 'STABLE' | 'DEGRADING';
  maintenance_recommendation:
    | 'NO_ACTION'
    | 'MONITOR'
    | 'ROUTINE_CALIBRATION'
    | 'PRIORITY_INSPECTION'
    | 'IMMEDIATE_INTERVENTION';
  component_scores: ComponentHealthScores;
  parameter_health?: Record<
    string,
    {
      score: number;
      status: string;
      trend: string;
      channel_id?: string;
    }
  >;
  history?: Array<{
    timestamp: string;
    score: number;
  }>;
}

export interface CorrectionRecommendation {
  observation_id: string;
  station_id: string;
  station_name?: string;
  timestamp: string;
  target_variable: string;
  observed_value: number;
  recommended_value: number | null;
  status:
    | 'REVIEW_REQUIRED'
    | 'CORRECTION_CANDIDATE'
    | 'IMPUTED'
    | 'ACCEPTED'
    | 'REJECTED'
    | 'NO_ACTION_REQUIRED';
  method: string;
  decision_type: string;
  reason_codes: string[];
  supporting_evidence: string[];
  uncertainty?: {
    lower_bound: number;
    upper_bound: number;
    confidence_level: number;
    quality_grade: string;
  };
  certainty_index?: number;
  multivariate_consistent: boolean;
  station_health_score?: number | null;
  station_health_band?: string | null;
  operator_summary: string;
  supporting_neighbors_count?: number;
  supporting_neighbors?: string[];
  audit_metadata?: {
    imputation_engine_version?: string;
    decision_engine_version?: string;
    generated_at?: string;
    is_causal_mode?: boolean;
  };
  created_at?: string;
}

export interface SystemComponentHealth {
  name: string;
  status: 'OK' | 'WARN' | 'ERROR';
  details: string;
  latency_ms?: number;
}

export interface PipelineLatencyItem {
  stage: string;
  p50_ms: number;
  p95_ms: number;
  target_sla: string;
  passed: boolean;
}

export interface ReplayStatus {
  is_active: boolean;
  mode: string;
  current_step: number;
  total_steps: number;
  emitted_packets: number;
  queued_packets: number;
  last_emitted_timestamp?: string;
}

export interface SystemHealthStatus {
  status: 'OPERATIONAL' | 'DEGRADED' | 'OUTAGE';
  uptime_seconds: number;
  uptime_human?: string;
  api_version: string;
  components: SystemComponentHealth[];
  latency_breakdown: PipelineLatencyItem[];
  replay_status?: ReplayStatus;
  monitored_stations_count?: number;
  total_observations_processed?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
