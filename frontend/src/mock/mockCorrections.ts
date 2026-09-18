/**
 * SkyGuard AI — Advisory Correction Recommendations Mock Data
 * Human-in-the-Loop advisory review layer. Non-destructive derived records.
 */

import { CorrectionRecommendation } from '../types/api';

export const MOCK_CORRECTIONS: CorrectionRecommendation[] = [
  {
    observation_id: 'OBS-42182099999-0735',
    station_id: '42182099999',
    station_name: 'NEW DELHI / SAFDARJUNG',
    timestamp: '2026-09-17T07:35:00 UTC',
    target_variable: 'temperature_c',
    observed_value: 58.5,
    recommended_value: 25.75,
    status: 'REVIEW_REQUIRED',
    method: 'SPATIAL_IDW_CONSENSUS',
    decision_type: 'UNCERTAIN',
    reason_codes: ['ML_HIGH_ANOMALY_SCORE', 'INSUFFICIENT_SPATIAL_CONTEXT'],
    supporting_evidence: [
      '3/3 neighboring stations report 25.4°C to 26.6°C',
      'August-Roche-Magnus thermodynamic balance satisfied at 25.75°C',
      'Physical elevation lapse rate applied (-0.65°C/100m)',
    ],
    uncertainty: {
      lower_bound: 25.15,
      upper_bound: 26.35,
      confidence_level: 0.95,
      quality_grade: 'HIGH',
    },
    certainty_index: 0.88,
    multivariate_consistent: true,
    station_health_score: 87,
    station_health_band: 'GOOD',
    supporting_neighbors_count: 3,
    supporting_neighbors: ['42184099999 (1.1km)', '42181099999 (8.9km)', '42187099999 (18.9km)'],
    operator_summary:
      'Candidate correction derived via spatial inverse-distance weighting (IDW) from 3 neighboring Delhi AWS nodes. Resolves sharp unphysical delta while strictly preserving raw sensor reading in immutable telemetry store.',
    audit_metadata: {
      imputation_engine_version: 'imputation_v1.0.0',
      decision_engine_version: 'hybrid_v1.0.0',
      is_causal_mode: true,
      generated_at: '2026-09-17T07:35:08Z',
    },
    created_at: '2026-09-17T07:35:08Z',
  },
  {
    observation_id: 'OBS-AWS007-0632',
    station_id: 'AWS_007',
    station_name: 'JAIPUR SANGANER',
    timestamp: '2026-09-17T06:32:00 UTC',
    target_variable: 'pressure_hpa',
    observed_value: 1001.4,
    recommended_value: 1012.9,
    status: 'CORRECTION_CANDIDATE',
    method: 'SPATIAL_IDW_CONSENSUS',
    decision_type: 'PROBABLE_SENSOR_ANOMALY',
    reason_codes: ['LOCAL_SPATIAL_ISOLATION'],
    supporting_evidence: [
      'Barometric offset verified across Jaipur regional ring',
      'Mean sea-level reduction formula calibrated for 390m elevation',
    ],
    uncertainty: {
      lower_bound: 1011.8,
      upper_bound: 1014.0,
      confidence_level: 0.95,
      quality_grade: 'HIGH',
    },
    certainty_index: 0.91,
    multivariate_consistent: true,
    station_health_score: 74,
    station_health_band: 'ATTENTION',
    supporting_neighbors_count: 3,
    supporting_neighbors: ['AWS_002 (18.4km)', 'AWS_011 (24.1km)', 'AWS_018 (31.0km)'],
    operator_summary:
      'Barometric sensor step offset detected. Recommended estimate aligns with regional synoptic pressure trend.',
    audit_metadata: {
      imputation_engine_version: 'imputation_v1.0.0',
      decision_engine_version: 'hybrid_v1.0.0',
      is_causal_mode: true,
      generated_at: '2026-09-17T06:32:09Z',
    },
    created_at: '2026-09-17T06:32:09Z',
  },
  {
    observation_id: 'OBS-AWS014-1303',
    station_id: 'AWS_014',
    station_name: 'CHURU OBSERVATORY',
    timestamp: '2026-09-17T13:03:00 UTC',
    target_variable: 'temperature_c',
    observed_value: 52.1,
    recommended_value: 28.4,
    status: 'REVIEW_REQUIRED',
    method: 'COMBINED_TEMPORAL_SPATIAL',
    decision_type: 'PROBABLE_SENSOR_ANOMALY',
    reason_codes: ['RAPID_RATE_OF_CHANGE', 'OUT_OF_RANGE_PHYSICAL'],
    supporting_evidence: [
      'Spike magnitude exceeds planetary bounds for September climate in Churu district',
      'Pre-spike baseline was 28.1°C with 0.1°C/min temporal gradient',
    ],
    uncertainty: {
      lower_bound: 27.8,
      upper_bound: 29.0,
      confidence_level: 0.95,
      quality_grade: 'MEDIUM',
    },
    certainty_index: 0.85,
    multivariate_consistent: true,
    station_health_score: 43,
    station_health_band: 'DEGRADED',
    supporting_neighbors_count: 2,
    operator_summary:
      'Hardware electrical glitch detected. Single-packet impulse departs by +23.8°C from autoregressive lag and spatial neighbors.',
    audit_metadata: {
      imputation_engine_version: 'imputation_v1.0.0',
      decision_engine_version: 'hybrid_v1.0.0',
      is_causal_mode: true,
      generated_at: '2026-09-17T13:03:05Z',
    },
    created_at: '2026-09-17T13:03:05Z',
  },
];
