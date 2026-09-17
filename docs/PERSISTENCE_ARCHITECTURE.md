# SkyGuard AI — Production Persistence & Data Lifecycle Architecture

## 1. Executive Summary & Prime Directives

SkyGuard AI is an operational meteorological data quality, anomaly detection, and sensor health monitoring platform. In Phase 12A, the system transitions from volatile in-memory storage to an enterprise-grade production persistence architecture using **SQLAlchemy 2.0** and **Alembic**.

The persistence layer satisfies four critical guarantees:
1. **Raw Observation Immutability**: Original raw incoming telemetry is append-only and strictly immutable. Derived flags, calibrations, imputations, and advisory repairs are stored in isolated relational entities.
2. **Deterministic Idempotency**: Deduplication keys prevent duplicate database writes during upstream network timeouts, polling retries, simulator replays, and process restarts.
3. **Causal & Historical Reproducibility**: Model IDs, feature engineering versions, decision engine versions, and explanation versions are permanently bound to all analytical outputs.
4. **Resilient Failure Degradation**: Connectivity or disk failures to the relational database degrade persistence telemetry while maintaining non-blocking real-time in-memory streaming pipelines.

---

## 2. Database Targets & Framework Architecture

- **Production Primary Target**: **PostgreSQL 14+** (using `psycopg2` or `asyncpg` drivers).
- **Development & Test Target**: **SQLite 3.37+** with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), synchronous normal, and strict foreign keys enabled.
- **ORM & Data Access**: SQLAlchemy 2.0 Declarative Mappings (`Mapped`, `mapped_column`) with explicit connection pooling (`pool_size`, `max_overflow`, `pool_pre_ping=True`).
- **Schema Evolution**: **Alembic** migrations with auto-migration support on server startup.

---

## 3. Entity-Relationship & Domain Model

```mermaid
erDiagram
    STATIONS ||--o{ OBSERVATIONS : "reports"
    STATIONS ||--o{ ANOMALY_EVENTS : "detects"
    STATIONS ||--o{ SENSOR_HEALTH_SNAPSHOTS : "evaluates"
    STATIONS ||--o{ CORRECTION_RECOMMENDATIONS : "recommends"
    ANOMALY_EVENTS ||--|| ANOMALY_EXPLANATIONS : "explains"
    
    STATIONS {
        string station_id PK
        string name
        float latitude
        float longitude
        float elevation_m
        string state
        string status
        int sampling_interval_seconds
        json installed_sensors
        timestamptz created_at
        timestamptz updated_at
    }

    OBSERVATIONS {
        int id PK
        string observation_id UK
        string station_id FK
        timestamptz observation_timestamp
        timestamptz ingestion_timestamp
        float temperature_c
        float relative_humidity_pct
        float dew_point_c
        float sea_level_pressure_hpa
        float station_pressure_hpa
        float latitude
        float longitude
        float elevation
        string source
        string report_type
        string data_quality_status
        boolean is_synthetic
        json raw_quality_flags
        json metadata_json
        timestamptz created_at
    }

    RAW_SOURCE_PAYLOADS {
        int id PK
        string payload_id UK
        string source
        string provider
        string endpoint
        string station_id
        timestamptz source_timestamp
        timestamptz retrieval_timestamp
        json raw_payload_json
        json headers_metadata
        string normalization_version
        timestamptz created_at
    }

    ANOMALY_EVENTS {
        int id PK
        string event_id UK
        string station_id FK
        timestamptz timestamp
        timestamptz created_at
        string decision
        string severity
        json reason_codes
        json observed_values
        json recommended_values
        text explanation_summary
        string model_id
        string model_version
        string feature_version
        string decision_engine_version
        boolean is_resolved
    }

    ANOMALY_EXPLANATIONS {
        int id PK
        string event_id UK,FK
        string station_id
        timestamptz timestamp
        json feature_attributions
        json spatial_evidence
        json temporal_evidence
        json multivariate_evidence
        json evidence_hierarchy
        text natural_language_explanation
        json recommended_sop_steps
        string explanation_version
        string model_id
        timestamptz created_at
    }

    SOURCE_HEALTH_TRANSITIONS {
        int id PK
        string source
        string from_state
        string to_state
        text reason
        string trigger_category
        json metadata_json
        timestamptz transition_timestamp
        timestamptz created_at
    }

    OUTAGE_EPISODES {
        int id PK
        string episode_id UK
        string source
        timestamptz started_at
        timestamptz resolved_at
        string initial_state
        string current_state
        float duration_seconds
        json affected_stations
        json failure_categories
        int observation_loss_estimate
        string assumptions_version
        boolean is_ongoing
        timestamptz created_at
        timestamptz updated_at
    }

    SENSOR_HEALTH_SNAPSHOTS {
        int id PK
        string station_id FK
        timestamptz timestamp
        float overall_health_score
        string status_band
        string trend
        string maintenance_recommendation
        json parameter_health
        json component_scores
        int active_anomalies_count
        string health_engine_version
        timestamptz created_at
    }

    CORRECTION_RECOMMENDATIONS {
        int id PK
        string observation_id UK
        string station_id FK
        timestamptz timestamp
        string target_variable
        float observed_value
        float recommended_value
        string status
        string method
        float confidence_lower
        float confidence_upper
        json uncertainty_json
        boolean multivariate_consistent
        json reason_codes
        text operator_summary
        string correction_engine_version
        timestamptz created_at
    }
```

---

## 4. Immutability & Data Integrity Rules

| Domain | Immutability Principle | Storage Destination | Modification Rule |
|---|---|---|---|
| **Raw Telemetry** | Absolute | `observations` | **Never** mutated. `temperature_c`, `pressure`, `humidity` reflect pristine sensor readings. |
| **Raw Payloads** | Absolute | `raw_source_payloads` | Preserves verbatim API response payloads. Secrets/credentials stripped from headers. |
| **QC & Classification** | Traceable | `observations.data_quality_status` | Initial QC classification captured at ingestion. |
| **Anomaly Events** | Append-Only | `anomaly_events` | Immutable historical record of analytical decisions. |
| **Explainability** | Permanent | `anomaly_explanations` | Preserves local SHAP attributions and spatial neighbor state at the exact moment of inference. |
| **Sensor Health** | Snapshot Series | `sensor_health_snapshots` | Periodic historical snapshots for long-term drift and degradation tracking. |
| **Advisory Repairs** | Segregated | `correction_recommendations` | Recommends candidate estimates with uncertainty intervals; raw observation remains unchanged. |

---

## 5. Deterministic Idempotency & Unique Constraints

To tolerate duplicate API observation packets, polling retries, and network replays, deterministic uniqueness keys are enforced at both the application and database levels:

1. **Observations Idempotency**:
   - Unique Constraint: `(source, station_id, observation_timestamp)`
   - Unique Identifier: `obs_{source}_{station_id[-6:]}_{sha256(source::station_id::timestamp)[:16]}`
   - Action on duplicate: Safely skipped (`DUPLICATE_SKIPPED`), existing row untouched.
2. **Anomaly Events Idempotency**:
   - Unique Constraint: `event_id` (`ANOM-{YYYYMMDD}-{STATION_ID}-{COUNTER}`)
3. **Outage Episodes Idempotency**:
   - Unique Constraint: `episode_id` (`ep_{YYYYMMDD_HHMMSS}_{COUNTER}`)
4. **Correction Recommendations Idempotency**:
   - Unique Constraint: `observation_id`

---

## 6. Indexing Strategy

Indexes are aligned with high-frequency operational and investigative queries:

| Table | Index Name | Indexed Columns | Query Purpose |
|---|---|---|---|
| `observations` | `ix_obs_station_time` | `(station_id, observation_timestamp)` | Chronological station time-series drilldown |
| `observations` | `ix_obs_source_time` | `(source, observation_timestamp)` | Multi-station batch synchronization by source |
| `anomaly_events` | `ix_anom_station_time` | `(station_id, timestamp)` | Active station alerts & 24h event counts |
| `anomaly_explanations`| `ix_anomaly_explanations_event_id` | `(event_id)` | 1-to-1 explainability drilldown |
| `source_health_transitions`| `ix_source_trans_time` | `(source, transition_timestamp)` | Operational uptime audit |
| `outage_episodes` | `ix_outage_source_started` | `(source, started_at)` | Incident review & loss calculations |
| `sensor_health_snapshots` | `ix_health_station_time` | `(station_id, timestamp)` | Long-term degradation and drift trends |
| `correction_recommendations`| `ix_corr_station_time` | `(station_id, timestamp)` | Operator candidate repair review |

---

## 7. Time Semantics & Normalization

- **All timestamps are normalized to UTC**: Persisted as ISO 8601 with timezone offset (`DateTime(timezone=True)` in PostgreSQL, UTC-assumed ISO strings in SQLite).
- **Distinction of Timestamps**:
  1. `observation_timestamp`: Scientific timestamp when sensor measured physical atmospheric state.
  2. `ingestion_timestamp`: Wall-clock timestamp when packet entered the SkyGuard ingestion pipeline.
  3. `transition_timestamp`: Operational timestamp when live source health state changed.
  4. `started_at` / `resolved_at`: Outage episode boundary timestamps.
  5. `created_at`: Database row insertion timestamp.

---

## 8. Configurable Data Lifecycle & Retention

Data retention policies are configurable via `StorageSettings` and environment variables. The default policy is **non-destructive** (`-1` indicates retain indefinitely).

```yaml
storage:
  observation_retention_days: -1        # -1 = retain indefinitely
  raw_payload_retention_days: -1        # -1 = retain indefinitely
  anomaly_retention_days: -1            # -1 = retain indefinitely
  sensor_health_retention_days: -1      # -1 = retain indefinitely
  source_health_retention_days: -1      # -1 = retain indefinitely
  outage_episode_retention_days: -1     # -1 = retain indefinitely
  correction_retention_days: -1         # -1 = retain indefinitely
```

When positive retention thresholds are configured (e.g. `observation_retention_days: 90`), `RetentionPolicyManager.prune_expired_records()` deletes records older than `now - interval` within a scoped database transaction.

---

## 9. Failure Modes & Degradation Handling

```mermaid
flowchart TD
    Obs[Incoming WeatherObservation] --> Engine[RealTimeProcessingEngine]
    Engine --> Pipeline[ML & Physics Processing]
    Pipeline --> Repo[DatabaseRepository]
    
    Repo --> CheckDB{Database Connected?}
    CheckDB -- Yes --> CommitDB[Commit Transaction to PostgreSQL/SQLite]
    CheckDB -- Connection Error / Disk Full --> Degrade[Set persistence_degraded = True]
    
    Degrade --> MemoryCache[Maintain Bounded In-Memory State Buffer]
    CommitDB --> MemoryCache
    MemoryCache --> Broadcast[Broadcast Real-Time WebSocket Events]
    MemoryCache --> Resp[Return ProcessingResult to Client]
    
    subgraph Observability
        Degrade --> Log[Log Error with Context]
        Degrade --> Metric[Increment write_failures Metric]
        Degrade --> HealthAPI[Expose database_status: DEGRADED on /system/health]
    end
```

- If database connectivity drops:
  1. In-memory station buffers and ML inference pipelines **continue operating without interruption**.
  2. Real-time WebSocket streaming continues broadcasting alerts.
  3. Repository logs the failure and marks `persistence_degraded = True`.
  4. `/api/v1/system/health` reports `database_status: "DEGRADED"` or `"DISCONNECTED"`.
  5. The pipeline never falsely asserts durable persistence when the database is unreachable.

---

## 10. Local Development & PostgreSQL Setup

### Quickstart (Local SQLite - Default)
No setup required. SQLite WAL database is automatically initialized at `./data/skyguard_dev.db`.

### Production PostgreSQL Setup
1. Start PostgreSQL container or managed instance:
   ```bash
   docker run --name skyguard-postgres -e POSTGRES_USER=skyguard_user -e POSTGRES_PASSWORD=skyguard_password -e POSTGRES_DB=skyguard_ai -p 5432:5432 -d postgres:16-alpine
   ```
2. Configure `.env`:
   ```bash
   SKYGUARD_DATABASE_URL=postgresql://skyguard_user:skyguard_password@localhost:5432/skyguard_ai
   SKYGUARD_STORAGE_POOL_SIZE=10
   SKYGUARD_STORAGE_MAX_OVERFLOW=20
   SKYGUARD_STORAGE_AUTO_MIGRATE=true
   ```
3. Run Alembic migrations:
   ```bash
   python -c "from backend.app.db.migrations import run_db_migrations; run_db_migrations()"
   ```
