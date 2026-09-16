"""Unit tests for Imputation Evaluator and Storage Persistence."""

import os
import shutil
from pathlib import Path
import pytest

from ml.imputation.evaluator import ImputationEvaluator
from ml.imputation.schema import (
    CorrectionRecommendation,
    EstimationMethod,
    ImputationRecord,
    ImputationStatus,
    RecommendationStatus,
)
from ml.imputation.storage import CorrectionStorageManager
from ml.spatial.engine import SpatialContextEngine
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def eval_topology():
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="STN_TEST", name="Test Station", latitude=28.6, longitude=77.2, elevation_m=200.0))
    topo.add_station(StationNode(station_id="N1", name="Neighbor 1", latitude=28.58, longitude=77.23, elevation_m=200.0))
    topo.add_station(StationNode(station_id="N2", name="Neighbor 2", latitude=28.62, longitude=77.19, elevation_m=200.0))
    return topo


def test_clean_data_protection_benchmark():
    evaluator = ImputationEvaluator()

    # 30 clean nominal observations
    clean_series = [25.0 + 0.1 * i for i in range(30)]
    corrupted_series = list(clean_series)  # No corruption
    labels = [0] * 30  # All clean
    timestamps = [f"2026-09-17T12:{i:02d}:00Z" for i in range(30)]

    metrics = evaluator.evaluate_synthetic_reconstruction(
        clean_values=clean_series,
        corrupted_values=corrupted_series,
        anomaly_labels=labels,
        timestamps=timestamps,
        station_id="STN_TEST",
    )

    assert metrics.total_clean_points == 30
    assert metrics.total_anomalous_points == 0
    assert metrics.unnecessary_correction_rate == 0.0
    assert metrics.candidates_count == 0
    assert metrics.no_correction_count == 30


def test_synthetic_anomaly_reconstruction_benchmark(eval_topology):
    spatial_engine = SpatialContextEngine(topology=eval_topology)
    evaluator = ImputationEvaluator()
    evaluator.correction_engine.spatial_engine = spatial_engine
    evaluator.imputer.spatial_engine = spatial_engine

    # 20 points with 4 injected anomalies (spikes and missing values)
    clean_series = [24.0 + 0.2 * (i % 5) for i in range(20)]
    corrupted_series = list(clean_series)
    labels = [0] * 20

    # Inject spike at index 5
    corrupted_series[5] = 45.0
    labels[5] = 1

    # Inject missing at index 10
    corrupted_series[10] = None
    labels[10] = 1

    # Inject spike at index 15
    corrupted_series[15] = 50.0
    labels[15] = 1

    timestamps = [f"2026-09-17T12:{i:02d}:00Z" for i in range(20)]

    neighbors = [
        {"station_id": "N1", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 24.5},
        {"station_id": "N2", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 24.6},
    ]

    metrics = evaluator.evaluate_synthetic_reconstruction(
        clean_values=clean_series,
        corrupted_values=corrupted_series,
        anomaly_labels=labels,
        timestamps=timestamps,
        station_id="STN_TEST",
        neighbor_data_pool=neighbors,
    )

    assert metrics.total_anomalous_points == 3
    assert metrics.correction_coverage >= 0.66
    assert metrics.mae is not None
    # Error vs clean ground truth should be low (< 2.0°C)
    assert metrics.mae < 2.0
    assert metrics.unnecessary_correction_rate == 0.0


def test_storage_manager_roundtrip(tmp_path):
    storage = CorrectionStorageManager(storage_dir=tmp_path / "corrections")

    imp_rec = ImputationRecord(
        station_id="STN_AUDIT",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        imputed_value=25.5,
        status=ImputationStatus.IMPUTED,
        method=EstimationMethod.CAUSAL_TEMPORAL_INTERPOLATION,
        reason="Test reason",
    )
    storage.save_imputation_record(imp_rec)

    corr_rec = CorrectionRecommendation(
        observation_id="audit_hash_1",
        station_id="STN_AUDIT",
        timestamp="2026-09-17T12:05:00Z",
        target_variable="temperature_c",
        observed_value=50.0,
        recommended_value=25.8,
        status=RecommendationStatus.CORRECTION_CANDIDATE,
        method=EstimationMethod.SPATIAL_IDW_CONSENSUS,
        decision_type="PROBABLE_SENSOR_ANOMALY",
        operator_summary="Test audit recommendation.",
    )
    storage.save_correction_recommendation(corr_rec)

    loaded_imps = storage.load_imputation_records(station_id="STN_AUDIT")
    assert len(loaded_imps) == 1
    assert loaded_imps[0]["station_id"] == "STN_AUDIT"
    assert loaded_imps[0]["imputed_value"] == 25.5

    loaded_corrs = storage.load_correction_recommendations(station_id="STN_AUDIT")
    assert len(loaded_corrs) == 1
    assert loaded_corrs[0]["observation_id"] == "audit_hash_1"
    assert loaded_corrs[0]["recommended_value"] == 25.8
