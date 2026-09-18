/**
 * SkyGuard AI — Anomaly Event Records & Explainability Packages Mock Data
 * Direct translation of OpenAPI 3.1 schema and screenshots.
 */

import { AnomalyEventRecord, ExplanationSummary } from '../types/api';

export const MOCK_ANOMALIES: AnomalyEventRecord[] = [
  {
    event_id: 'ANOM-20260917-099999-0004',
    station_id: '42182099999',
    station_name: 'NEW DELHI / SAFDARJUNG',
    timestamp: '2026-09-17T07:35:00 UTC',
    decision: 'UNCERTAIN',
    severity: 'MEDIUM',
    reason_codes: [
      'ML_HIGH_ANOMALY_SCORE',
      'INSUFFICIENT_SPATIAL_CONTEXT',
      'CONFLICTING_EVIDENCE',
    ],
    observed_values: {
      temperature_c: 58.5,
      humidity_pct: 10.0,
      pressure_hpa: 1013.25,
    },
    recommended_values: {
      temperature_c: 25.75,
      humidity_pct: 59.8,
      pressure_hpa: 1013.25,
    },
    expected_values: {
      temperature_c: 26.2,
      humidity_pct: 59.4,
      pressure_hpa: 985.8,
    },
    explanation_summary:
      'Uncertain classification: ML anomaly detector flagged elevated residual (score: 1.00), but spatial neighbors confirm regional baseline envelope.',
    created_at: '2026-09-17T07:35:05Z',
    duration_minutes: 14,
    onset_timestamp: '2026-09-17 07:35 UTC',
    peak_timestamp: '2026-09-17 07:35 UTC',
    peak_value: 58.5,
    target_variable: 'temperature_c',
  },
  {
    event_id: 'ANOM-20260917-099999-0003',
    station_id: '42182099999',
    station_name: 'NEW DELHI / SAFDARJUNG',
    timestamp: '2026-09-17T07:30:00 UTC',
    decision: 'UNCERTAIN',
    severity: 'MEDIUM',
    reason_codes: ['ML_MODERATE_ANOMALY_SCORE', 'INSUFFICIENT_SPATIAL_CONTEXT'],
    observed_values: {
      temperature_c: 51.2,
      humidity_pct: 14.0,
      pressure_hpa: 1013.2,
    },
    recommended_values: {
      temperature_c: 25.8,
      humidity_pct: 59.5,
      pressure_hpa: 1013.2,
    },
    explanation_summary:
      'Uncertain classification: ML anomaly detector flagged elevated residual (score: 0.72), but spatial context is sparsely distributed.',
    created_at: '2026-09-17T07:30:02Z',
    duration_minutes: 9,
    target_variable: 'temperature_c',
  },
  {
    event_id: 'ANOM-20260917-099999-0002',
    station_id: '42182099999',
    station_name: 'NEW DELHI / SAFDARJUNG',
    timestamp: '2026-09-17T06:40:00 UTC',
    decision: 'UNCERTAIN',
    severity: 'MEDIUM',
    reason_codes: ['ML_HIGH_ANOMALY_SCORE'],
    observed_values: {
      temperature_c: 48.0,
      humidity_pct: 18.0,
      pressure_hpa: 1013.0,
    },
    recommended_values: {
      temperature_c: 25.4,
    },
    explanation_summary:
      'Uncertain classification: ML anomaly detector flagged elevated residual (score: 1.00), but spatial neighbors indicate stable microclimate.',
    created_at: '2026-09-17T06:40:02Z',
    duration_minutes: 5,
    target_variable: 'temperature_c',
  },
  {
    event_id: 'ANOM-20260917-099999-0001',
    station_id: '42182099999',
    station_name: 'NEW DELHI / SAFDARJUNG',
    timestamp: '2026-09-17T06:35:00 UTC',
    decision: 'UNCERTAIN',
    severity: 'MEDIUM',
    reason_codes: ['ML_MODERATE_ANOMALY_SCORE'],
    observed_values: {
      temperature_c: 38.2,
      humidity_pct: 35.0,
      pressure_hpa: 1013.1,
    },
    recommended_values: {
      temperature_c: 25.1,
    },
    explanation_summary:
      'Uncertain classification: ML anomaly detector flagged elevated residual (score: 0.63), but spatial context is consistent.',
    created_at: '2026-09-17T06:35:02Z',
    duration_minutes: 5,
    target_variable: 'temperature_c',
  },
  {
    event_id: 'ANOM-20260917-STN_001-0002',
    station_id: 'AWS_007',
    station_name: 'JAIPUR SANGANER',
    timestamp: '2026-09-17T06:32:00 UTC',
    decision: 'PROBABLE_SENSOR_ANOMALY',
    severity: 'HIGH',
    reason_codes: ['LOCAL_SPATIAL_ISOLATION', 'ML_HIGH_ANOMALY_SCORE'],
    observed_values: {
      pressure_hpa: 1001.4,
      temperature_c: 31.1,
      humidity_pct: 71.0,
    },
    recommended_values: {
      pressure_hpa: 1012.9,
      temperature_c: 28.4,
    },
    expected_values: {
      pressure_hpa: 1013.2,
      temperature_c: 28.3,
    },
    explanation_summary:
      'Local spatial isolation: Barometric pressure -11.8 hPa departure from 3/3 neighboring stations. ML anomaly score 0.81 exceeds calibrated threshold.',
    created_at: '2026-09-17T06:32:05Z',
    duration_minutes: 18,
    onset_timestamp: '2026-09-17 06:14 UTC',
    peak_timestamp: '2026-09-17 06:25 UTC',
    peak_value: 1001.4,
    target_variable: 'pressure_hpa',
  },
  {
    event_id: 'ANOM-20260917-CRIT-0014',
    station_id: 'AWS_014',
    station_name: 'CHURU OBSERVATORY',
    timestamp: '2026-09-17T13:03:00 UTC',
    decision: 'PROBABLE_SENSOR_ANOMALY',
    severity: 'CRITICAL',
    reason_codes: [
      'RAPID_RATE_OF_CHANGE',
      'OUT_OF_RANGE_PHYSICAL',
      'LOCAL_SPATIAL_ISOLATION',
    ],
    observed_values: {
      temperature_c: 52.1,
      humidity_pct: 44.0,
      pressure_hpa: 1015.1,
    },
    recommended_values: {
      temperature_c: 28.4,
    },
    expected_values: {
      temperature_c: 28.3,
    },
    explanation_summary:
      'Critical sensor anomaly: Rapid unphysical temperature spike (+23.8°C departure vs spatial baseline 28.3°C).',
    created_at: '2026-09-17T13:03:02Z',
    duration_minutes: 14,
    target_variable: 'temperature_c',
  },
  {
    event_id: 'ANOM-20260916-099999-0005',
    station_id: 'AWS_019',
    station_name: 'JODHPUR DESERT AWS',
    timestamp: '2026-09-16T18:30:00 UTC',
    decision: 'PROBABLE_DATA_QUALITY_ISSUE',
    severity: 'LOW',
    reason_codes: ['OUT_OF_ORDER_TIMESTAMP', 'DATA_GAP'],
    observed_values: {
      temperature_c: null,
      humidity_pct: null,
      pressure_hpa: null,
    },
    explanation_summary:
      'Data quality defect detected. Telemetry packet gap exceeded 30 minutes, followed by out-of-order sequence index.',
    created_at: '2026-09-16T18:30:01Z',
    duration_minutes: 34,
    target_variable: 'communication',
  },
];

export function getMockAnomalyExplanation(eventId: string): ExplanationSummary {
  const anom =
    MOCK_ANOMALIES.find((a) => a.event_id === eventId) || MOCK_ANOMALIES[0];

  return {
    station_id: anom.station_id,
    timestamp: anom.timestamp,
    decision: anom.decision,
    severity: anom.severity,
    summary: anom.explanation_summary,
    supporting_evidence: [
      'Single-station ML Isolation Forest scored residual above 0.80',
      'Local spatial isolation test: target sensor departs from nearest 3 topographic neighbors',
      'Direct physical validation: observed rate of change (+1.8°C/min) approaches hardware limit',
    ],
    contradicting_evidence: [
      'No synoptic regional storm or heatwave advisory in effect for district',
      'Thermodynamic vapor consistency test failed against concurrent wet bulb depression',
    ],
    unavailable_evidence: [
      'Satellite thermal infrared surface temperature product unavailable for current hour',
    ],
    anomaly_score: 0.81,
    calibrated_threshold: 0.58,
    feature_contributions: [
      {
        feature: 'temp_rate_of_change',
        display_name: 'Temperature Rate of Change',
        value: 1.8,
        contribution: 0.384,
        direction: 'increases_anomaly',
        description: 'Rate of change exceeds typical 3-sigma diurnal velocity',
      },
      {
        feature: 'temp_zscore_1h',
        display_name: 'Temperature Z-Score (1h)',
        value: 4.12,
        contribution: 0.312,
        direction: 'increases_anomaly',
        description: 'Strong standard deviation departure from rolling 1-hour window',
      },
      {
        feature: 'pressure_delta_nbr',
        display_name: 'Pressure Delta vs Neighbors',
        value: -11.8,
        contribution: 0.142,
        direction: 'increases_anomaly',
        description: 'Significant isobaric deviation from nearest spatial AWS',
      },
      {
        feature: 'humidity_consistency',
        display_name: 'Thermodynamic RH Consistency',
        value: 0.18,
        contribution: -0.082,
        direction: 'decreases_anomaly',
        description: 'Relative humidity gradient consistent with Magnus curve',
      },
      {
        feature: 'temp_diurnal_residual',
        display_name: 'Diurnal Harmonic Residual',
        value: 2.4,
        contribution: 0.058,
        direction: 'increases_anomaly',
        description: 'Residual departure from climatological solar day harmonic',
      },
    ],
    spatial_evidence: {
      consensus: 'LOCAL_ONLY',
      neighbor_count: 3,
      agreeing_count: 0,
      disagreeing_count: 3,
      max_deviation: 11.8,
      neighbors: [
        {
          station_id: '42184099999',
          station_name: 'DELHI / LODHI ROAD',
          distance_km: 1.1,
          azimuth_deg: 42,
          temperature_c: 25.8,
          humidity_pct: 59.6,
          pressure_hpa: 986.9,
          status: 'DISAGREE',
        },
        {
          station_id: '42181099999',
          station_name: 'DELHI / PALAM',
          distance_km: 8.9,
          azimuth_deg: 260,
          temperature_c: 25.4,
          humidity_pct: 59.8,
          pressure_hpa: 983.6,
          status: 'DISAGREE',
        },
        {
          station_id: '42187099999',
          station_name: 'NOIDA AWS',
          distance_km: 18.9,
          azimuth_deg: 104,
          temperature_c: 26.6,
          humidity_pct: 59.2,
          pressure_hpa: 988.3,
          status: 'DISAGREE',
        },
      ],
    },
    temporal_evidence: {
      rate_of_change: 1.8,
      rate_unit: '°C/min',
      flatline_count: 0,
      zscore_1h: 4.12,
      diurnal_residual: 2.4,
      is_rate_exceeded: true,
    },
    data_quality_evidence: {
      quality_status: 'VALID',
      missing_fields: [],
      communication_gap_minutes: 0,
      is_duplicate: false,
      is_out_of_order: false,
      is_physical_out_of_bounds: false,
      evidence_state: 'NEUTRAL',
    },
    multivariate_evidence: {
      is_consistent: true,
      thermodynamic_status: 'PASS',
      rh_dewpoint_check: 'Valid Magnus RH consistency within ±3%',
      hypsometric_pressure_check: 'Barometric profile within barometric tolerance',
    },
    audit_metadata: {
      model_version: 'isolation_forest_v1',
      feature_version: 'v1.0.0',
      decision_engine_version: 'hybrid_v1.0.0',
      explanation_engine_version: 'xai_v1.0.0',
      explanation_method: 'TREE_SHAP',
      input_station_id: anom.station_id,
      input_timestamp: anom.timestamp,
      generated_at: '2026-09-17T07:35:10Z',
    },
    recommended_action:
      'Inspect physical sensor housing, aspirator fan, and cable terminations. Cross-verify against secondary portable reference barometer.',
  };
}
