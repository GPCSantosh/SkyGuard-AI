/**
 * SkyGuard AI — System Diagnostics & Replay Simulator Mock Data
 * Observability telemetry matching system status page and SLA benchmarks.
 */

import { SystemHealthStatus, ReplayStatus } from '../types/api';

export const MOCK_REPLAY_STATUS: ReplayStatus = {
  is_active: false,
  mode: 'SYNTHETIC_REPLAY',
  current_step: 0,
  total_steps: 240,
  emitted_packets: 0,
  queued_packets: 240,
  last_emitted_timestamp: '2026-09-17T13:05:00Z',
};

export const MOCK_SYSTEM_HEALTH: SystemHealthStatus = {
  status: 'OPERATIONAL',
  uptime_seconds: 1234567,
  uptime_human: '14d 06:43:22',
  api_version: 'v0.1.0 (FastAPI 0.115.0)',
  monitored_stations_count: 8,
  total_observations_processed: 48291,
  components: [
    {
      name: 'FastAPI Telemetry Core',
      status: 'OK',
      details: 'SkyGuard AI Real-Time Processing Engine v1.0.0',
      latency_ms: 0.21,
    },
    {
      name: 'Observation Persistence Store',
      status: 'OK',
      details: '8 monitored stations · 48,291 observations indexed in hypertable',
      latency_ms: 0.12,
    },
    {
      name: 'ML Model Registry',
      status: 'OK',
      details: 'Active Model: isolation_forest_s42 (Pre-trained & Calibrated)',
      latency_ms: 0.04,
    },
    {
      name: 'Hybrid Decision Engine',
      status: 'OK',
      details: 'Deterministic Multi-Tier Heuristic + ML Anomaly Fusion (v1.0.0)',
      latency_ms: 0.03,
    },
    {
      name: 'Explainability & XAI Engine',
      status: 'OK',
      details: 'TreeSHAP & Multi-Tier Evidence Synthesizer Active',
      latency_ms: 0.06,
    },
    {
      name: 'Spatial Topology Engine',
      status: 'OK',
      details: '8 Topographic Graph Nodes (Haversine/IDW Context)',
      latency_ms: 0.03,
    },
    {
      name: 'Stream Replay Simulator',
      status: 'OK',
      details: 'READY · 240 historical packets queued for validation stepping',
      latency_ms: 0.01,
    },
  ],
  latency_breakdown: [
    {
      stage: 'Total Ingestion-to-Decision Pipeline',
      p50_ms: 0.21,
      p95_ms: 5.89,
      target_sla: '< 15.0 ms',
      passed: true,
    },
    {
      stage: 'Feature Engineering & Lag Extraction',
      p50_ms: 0.08,
      p95_ms: 1.12,
      target_sla: '< 5.0 ms',
      passed: true,
    },
    {
      stage: 'Isolation Forest Inference',
      p50_ms: 0.04,
      p95_ms: 0.88,
      target_sla: '< 3.0 ms',
      passed: true,
    },
    {
      stage: 'Spatial Neighbor Topology Context',
      p50_ms: 0.03,
      p95_ms: 1.44,
      target_sla: '< 5.0 ms',
      passed: true,
    },
    {
      stage: 'TreeSHAP & Evidence Synthesizer',
      p50_ms: 0.06,
      p95_ms: 2.45,
      target_sla: '< 8.0 ms',
      passed: true,
    },
  ],
  replay_status: MOCK_REPLAY_STATUS,
};
