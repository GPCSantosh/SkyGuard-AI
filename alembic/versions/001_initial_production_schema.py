"""Initial production persistence schema for SkyGuard AI.

Revision ID: 001_initial
Revises: None
Create Date: 2026-09-17 11:55:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Stations Table
    op.create_table(
        'stations',
        sa.Column('station_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('elevation_m', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('state', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('sampling_interval_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('installed_sensors', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('station_id'),
    )
    op.create_index(op.f('ix_stations_station_id'), 'stations', ['station_id'], unique=False)

    # 2. Observations Table (Immutable Raw Telemetry)
    op.create_table(
        'observations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('observation_id', sa.String(length=128), nullable=False),
        sa.Column('station_id', sa.String(length=64), nullable=False),
        sa.Column('observation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('relative_humidity_pct', sa.Float(), nullable=True),
        sa.Column('dew_point_c', sa.Float(), nullable=True),
        sa.Column('sea_level_pressure_hpa', sa.Float(), nullable=True),
        sa.Column('station_pressure_hpa', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('elevation', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('report_type', sa.String(length=64), nullable=True),
        sa.Column('data_quality_status', sa.String(length=32), nullable=False, server_default='VALID'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('raw_quality_flags', sa.JSON(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('observation_id'),
        sa.UniqueConstraint('source', 'station_id', 'observation_timestamp', name='uq_obs_source_station_time'),
    )
    op.create_index(op.f('ix_observations_observation_id'), 'observations', ['observation_id'], unique=True)
    op.create_index(op.f('ix_observations_station_id'), 'observations', ['station_id'], unique=False)
    op.create_index(op.f('ix_observations_observation_timestamp'), 'observations', ['observation_timestamp'], unique=False)
    op.create_index(op.f('ix_observations_source'), 'observations', ['source'], unique=False)
    op.create_index('ix_obs_station_time', 'observations', ['station_id', 'observation_timestamp'], unique=False)
    op.create_index('ix_obs_source_time', 'observations', ['source', 'observation_timestamp'], unique=False)

    # 3. Raw Source Payloads Table
    op.create_table(
        'raw_source_payloads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('payload_id', sa.String(length=128), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('station_id', sa.String(length=64), nullable=True),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retrieval_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('raw_payload_json', sa.JSON(), nullable=False),
        sa.Column('headers_metadata', sa.JSON(), nullable=False),
        sa.Column('normalization_version', sa.String(length=64), nullable=False, server_default='v1.0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payload_id'),
    )
    op.create_index(op.f('ix_raw_source_payloads_payload_id'), 'raw_source_payloads', ['payload_id'], unique=True)
    op.create_index(op.f('ix_raw_source_payloads_source'), 'raw_source_payloads', ['source'], unique=False)
    op.create_index(op.f('ix_raw_source_payloads_station_id'), 'raw_source_payloads', ['station_id'], unique=False)
    op.create_index(op.f('ix_raw_source_payloads_retrieval_timestamp'), 'raw_source_payloads', ['retrieval_timestamp'], unique=False)
    op.create_index('ix_raw_source_retrieval', 'raw_source_payloads', ['source', 'retrieval_timestamp'], unique=False)

    # 4. Anomaly Events Table
    op.create_table(
        'anomaly_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('station_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decision', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('reason_codes', sa.JSON(), nullable=False),
        sa.Column('observed_values', sa.JSON(), nullable=False),
        sa.Column('recommended_values', sa.JSON(), nullable=False),
        sa.Column('explanation_summary', sa.Text(), nullable=True),
        sa.Column('model_id', sa.String(length=128), nullable=True),
        sa.Column('model_version', sa.String(length=64), nullable=True),
        sa.Column('feature_version', sa.String(length=64), nullable=False, server_default='v1.0.0'),
        sa.Column('decision_engine_version', sa.String(length=64), nullable=False, server_default='hybrid_v1.0.0'),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index(op.f('ix_anomaly_events_event_id'), 'anomaly_events', ['event_id'], unique=True)
    op.create_index(op.f('ix_anomaly_events_station_id'), 'anomaly_events', ['station_id'], unique=False)
    op.create_index(op.f('ix_anomaly_events_timestamp'), 'anomaly_events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_anomaly_events_decision'), 'anomaly_events', ['decision'], unique=False)
    op.create_index(op.f('ix_anomaly_events_severity'), 'anomaly_events', ['severity'], unique=False)
    op.create_index('ix_anom_station_time', 'anomaly_events', ['station_id', 'timestamp'], unique=False)

    # 5. Explanations Table
    op.create_table(
        'anomaly_explanations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('station_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('feature_attributions', sa.JSON(), nullable=False),
        sa.Column('spatial_evidence', sa.JSON(), nullable=False),
        sa.Column('temporal_evidence', sa.JSON(), nullable=False),
        sa.Column('multivariate_evidence', sa.JSON(), nullable=False),
        sa.Column('evidence_hierarchy', sa.JSON(), nullable=False),
        sa.Column('natural_language_explanation', sa.Text(), nullable=True),
        sa.Column('recommended_sop_steps', sa.JSON(), nullable=False),
        sa.Column('explanation_version', sa.String(length=64), nullable=False, server_default='v1.0.0'),
        sa.Column('model_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index(op.f('ix_anomaly_explanations_event_id'), 'anomaly_explanations', ['event_id'], unique=True)
    op.create_index(op.f('ix_anomaly_explanations_station_id'), 'anomaly_explanations', ['station_id'], unique=False)

    # 6. Source Health Transitions Table
    op.create_table(
        'source_health_transitions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('from_state', sa.String(length=32), nullable=False),
        sa.Column('to_state', sa.String(length=32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('trigger_category', sa.String(length=64), nullable=False, server_default='NONE'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('transition_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_source_health_transitions_source'), 'source_health_transitions', ['source'], unique=False)
    op.create_index(op.f('ix_source_health_transitions_to_state'), 'source_health_transitions', ['to_state'], unique=False)
    op.create_index(op.f('ix_source_health_transitions_transition_timestamp'), 'source_health_transitions', ['transition_timestamp'], unique=False)
    op.create_index('ix_source_trans_time', 'source_health_transitions', ['source', 'transition_timestamp'], unique=False)

    # 7. Outage Episodes Table
    op.create_table(
        'outage_episodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('episode_id', sa.String(length=128), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('initial_state', sa.String(length=32), nullable=False),
        sa.Column('current_state', sa.String(length=32), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('affected_stations', sa.JSON(), nullable=False),
        sa.Column('failure_categories', sa.JSON(), nullable=False),
        sa.Column('observation_loss_estimate', sa.Integer(), nullable=True),
        sa.Column('assumptions_version', sa.String(length=64), nullable=False, server_default='v1.0.0'),
        sa.Column('is_ongoing', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('episode_id'),
    )
    op.create_index(op.f('ix_outage_episodes_episode_id'), 'outage_episodes', ['episode_id'], unique=True)
    op.create_index(op.f('ix_outage_episodes_source'), 'outage_episodes', ['source'], unique=False)
    op.create_index(op.f('ix_outage_episodes_started_at'), 'outage_episodes', ['started_at'], unique=False)
    op.create_index(op.f('ix_outage_episodes_resolved_at'), 'outage_episodes', ['resolved_at'], unique=False)
    op.create_index(op.f('ix_outage_episodes_is_ongoing'), 'outage_episodes', ['is_ongoing'], unique=False)
    op.create_index('ix_outage_source_started', 'outage_episodes', ['source', 'started_at'], unique=False)

    # 8. Sensor Health Snapshots Table
    op.create_table(
        'sensor_health_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('station_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('overall_health_score', sa.Float(), nullable=True),
        sa.Column('status_band', sa.String(length=32), nullable=False),

        sa.Column('trend', sa.String(length=32), nullable=False, server_default='STABLE'),
        sa.Column('maintenance_recommendation', sa.String(length=64), nullable=False, server_default='NO_ACTION'),
        sa.Column('parameter_health', sa.JSON(), nullable=False),
        sa.Column('component_scores', sa.JSON(), nullable=False),
        sa.Column('active_anomalies_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('health_engine_version', sa.String(length=64), nullable=False, server_default='v1.0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sensor_health_snapshots_station_id'), 'sensor_health_snapshots', ['station_id'], unique=False)
    op.create_index(op.f('ix_sensor_health_snapshots_timestamp'), 'sensor_health_snapshots', ['timestamp'], unique=False)
    op.create_index('ix_health_station_time', 'sensor_health_snapshots', ['station_id', 'timestamp'], unique=False)

    # 9. Correction Recommendations Table
    op.create_table(
        'correction_recommendations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('observation_id', sa.String(length=128), nullable=False),
        sa.Column('station_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('target_variable', sa.String(length=64), nullable=False),
        sa.Column('observed_value', sa.Float(), nullable=True),
        sa.Column('recommended_value', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('method', sa.String(length=64), nullable=False),
        sa.Column('confidence_lower', sa.Float(), nullable=True),
        sa.Column('confidence_upper', sa.Float(), nullable=True),
        sa.Column('uncertainty_json', sa.JSON(), nullable=False),
        sa.Column('multivariate_consistent', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('reason_codes', sa.JSON(), nullable=False),
        sa.Column('operator_summary', sa.Text(), nullable=True),
        sa.Column('correction_engine_version', sa.String(length=64), nullable=False, server_default='v1.0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('observation_id'),
    )
    op.create_index(op.f('ix_correction_recommendations_observation_id'), 'correction_recommendations', ['observation_id'], unique=True)
    op.create_index(op.f('ix_correction_recommendations_station_id'), 'correction_recommendations', ['station_id'], unique=False)
    op.create_index(op.f('ix_correction_recommendations_timestamp'), 'correction_recommendations', ['timestamp'], unique=False)
    op.create_index(op.f('ix_correction_recommendations_target_variable'), 'correction_recommendations', ['target_variable'], unique=False)
    op.create_index(op.f('ix_correction_recommendations_status'), 'correction_recommendations', ['status'], unique=False)
    op.create_index('ix_corr_station_time', 'correction_recommendations', ['station_id', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('correction_recommendations')
    op.drop_table('sensor_health_snapshots')
    op.drop_table('outage_episodes')
    op.drop_table('source_health_transitions')
    op.drop_table('anomaly_explanations')
    op.drop_table('anomaly_events')
    op.drop_table('raw_source_payloads')
    op.drop_table('observations')
    op.drop_table('stations')
