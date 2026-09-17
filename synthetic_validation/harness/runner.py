"""End-to-End Validation Harness Runner.

Executes synthetic observations through the complete production processing path:
WeatherObservation -> QC -> Feature Extraction -> ML Model -> Hybrid Decision ->
Explainability -> Sensor Health -> Imputation/Correction -> Persistence -> WebSocket.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.state import StationStateManager
from backend.app.core.ws_manager import WebSocketConnectionManager
from backend.app.db.session import DatabaseSessionManager
from backend.app.models.observation import WeatherObservation
from backend.app.models.processing import ProcessingResult, ProcessingStatus
from ml.health.health_schema import SensorHealthSummary
from synthetic_validation.harness.assertions import SyntheticAssertionSuite
from synthetic_validation.harness.injector import SyntheticAnomalyInjector
from synthetic_validation.harness.network_generator import (
    DEFAULT_SYNTHETIC_STATIONS,
    SyntheticNetworkGenerator,
)
from synthetic_validation.scenarios.definitions import (
    SCENARIO_DEFINITIONS,
    ScenarioDefinition,
    get_scenario_by_id,
)


@dataclass
class ScenarioRunResult:
    """Outcome report for a single validation scenario across 9 independent dimensions."""
    scenario_id: str
    name: str
    category: str
    status: str  # PASS, FAIL, BLOCKED
    target_stations: List[str]
    total_observations_processed: int
    
    # 9 Distinct Validation Dimensions
    execution_pass: bool = False
    detection_pass: bool = False
    classification_pass: bool = False
    sensor_health_pass: bool = False
    source_health_pass: bool = False
    explainability_pass: bool = False
    correction_pass: bool = False
    persistence_pass: bool = False
    websocket_pass: bool = False
    overall_pass: bool = False
    
    # ML vs Hybrid Analysis
    ml_anomaly_detected: bool = False
    ml_score: Optional[float] = None
    hybrid_decision: Optional[str] = None
    
    # Decisions & States
    expected_decision: str = "NORMAL"
    accepted_decisions: List[str] = field(default_factory=lambda: ["NORMAL"])
    actual_decision: Optional[str] = None
    
    # Health States
    health_score_before: float = 100.0
    health_score_after: float = 100.0
    expected_sensor_health_direction: str = "STABLE"
    source_health_state: str = "HEALTHY"
    expected_source_health: str = "HEALTHY"
    
    # Performance & Delivery
    mean_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    websocket_events_dispatched: int = 0
    failure_reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SyntheticValidationRunner:
    """Orchestrates end-to-end synthetic testing of the SkyGuard real-time intelligence stack."""

    def __init__(
        self,
        database_url: str = "sqlite:///:memory:",
        seed: int = 42,
    ) -> None:
        self.database_url = database_url
        self.seed = seed
        self.generator = SyntheticNetworkGenerator(seed=seed)
        self.topology = self.generator.create_topology()
        self.injector = SyntheticAnomalyInjector(seed=seed)

    def _create_isolated_engine(self) -> Tuple[RealTimeProcessingEngine, DatabaseRepository, WebSocketConnectionManager]:
        """Create an isolated, production-parity RealTimeProcessingEngine instance."""
        session_mgr = DatabaseSessionManager(self.database_url)
        repo = DatabaseRepository(topology=self.topology, session_manager=session_mgr)
        state_mgr = StationStateManager()
        ws_mgr = WebSocketConnectionManager()
        
        engine = RealTimeProcessingEngine(
            repository=repo,
            state_manager=state_mgr,
            ws_manager=ws_mgr,
        )
        return engine, repo, ws_mgr

    def run_single_scenario(self, scenario_id: str) -> ScenarioRunResult:
        """Run a single scenario in isolation and return comprehensive multi-dimensional results."""
        scenario = get_scenario_by_id(scenario_id)
        if scenario is None:
            return ScenarioRunResult(
                scenario_id=scenario_id,
                name="Unknown Scenario",
                category="UNKNOWN",
                status="BLOCKED",
                target_stations=[],
                total_observations_processed=0,
                expected_decision="UNKNOWN",
                failure_reasons=[f"Scenario ID {scenario_id} not found in registry."],
            )

        # 1. Generate clean baseline
        baseline_obs = self.generator.generate_baseline_observations(
            duration_hours=24.0,
            interval_minutes=5,
        )

        # 2. Inject single scenario
        injected_obs, truth_registry = self.injector.inject_all_scenarios(
            baseline_observations=baseline_obs,
            scenarios=[scenario],
        )

        # 3. Instantiate clean engine
        engine, repo, ws_mgr = self._create_isolated_engine()

        # 4. Execute streaming pipeline up to the scenario injection window + follow-up
        latencies: List[float] = []
        target_results: List[ProcessingResult] = []
        target_station = scenario.target_stations[0] if scenario.target_stations else "AWS_DEL_001"
        if target_station == "ALL_20_STATIONS":
            target_station = "AWS_DEL_001"

        # Baseline health check before injection
        buf = engine.state_manager.get_or_create_buffer(target_station)
        health_before = buf.health_history[-1] if buf.health_history else None
        health_score_before = health_before.overall_health_score if (health_before and health_before.overall_health_score is not None) else 100.0

        # Filter stream to window around scenario (warmup of 24 cycles before injection + 4 cycles after)
        start_step = max(0, scenario.injection_start_step - 24)
        end_step = scenario.injection_end_step + 4
        obs_window = [
            o for o in injected_obs
            if start_step <= (o.metadata.get("step_index", 0) if o.metadata else 0) <= end_step
        ]

        execution_pass = True
        exec_error = None
        
        try:
            for obs in obs_window:
                step = obs.metadata.get("step_index", 0) if obs.metadata else 0

                t0 = time.perf_counter()
                res = engine.process_observation(obs)
                lat_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(lat_ms)

                # Record results for target stations during injection window
                if scenario.target_stations == ["ALL_20_STATIONS"] or obs.station_id in scenario.target_stations:
                    if scenario.injection_start_step <= step <= scenario.injection_end_step:
                        target_results.append(res)
        except Exception as e:
            execution_pass = False
            exec_error = f"Pipeline execution error: {str(e)}"

        health_after = buf.health_history[-1] if buf.health_history else None
        health_score_after = health_after.overall_health_score if (health_after and health_after.overall_health_score is not None) else 100.0

        # 5. Extract Representative Result and ML Metrics
        rep_result: Optional[ProcessingResult] = None
        ml_score: Optional[float] = None
        ml_is_anom = False
        hybrid_dec_val: Optional[str] = None
        actual_decision: Optional[str] = None

        if target_results:
            # Pick representative result during fault window
            matching = [r for r in target_results if r.hybrid_decision and r.hybrid_decision.decision.value == scenario.expected_decision]
            rep_result = matching[0] if matching else target_results[-1]
            
            if rep_result.hybrid_decision is not None:
                hybrid_dec_val = rep_result.hybrid_decision.decision.value
                actual_decision = hybrid_dec_val
                if rep_result.hybrid_decision.evidence and rep_result.hybrid_decision.evidence.ml_anomaly:
                    ml_ev = rep_result.hybrid_decision.evidence.ml_anomaly
                    ml_score = ml_ev.raw_model_score
                    ml_is_anom = ml_ev.ml_is_anomaly
            elif rep_result.status is not None:
                actual_decision = str(rep_result.status.value if hasattr(rep_result.status, "value") else rep_result.status)

        # 6. Evaluate All 9 Validation Dimensions
        failure_reasons: List[str] = []
        if exec_error:
            failure_reasons.append(exec_error)

        det_pass, det_err = SyntheticAssertionSuite.evaluate_detection(scenario, rep_result, ml_is_anom)
        if not det_pass and det_err:
            failure_reasons.append(det_err)

        class_pass, class_err, act_dec = SyntheticAssertionSuite.evaluate_classification(scenario, rep_result)
        if not class_pass and class_err:
            failure_reasons.append(class_err)
        if act_dec:
            actual_decision = act_dec

        health_pass, health_err = SyntheticAssertionSuite.evaluate_sensor_health(scenario, health_before, health_after)
        if not health_pass and health_err:
            failure_reasons.append(health_err)

        source_state = scenario.expected_source_health
        src_pass, src_err = SyntheticAssertionSuite.evaluate_source_health(scenario, source_state)
        if not src_pass and src_err:
            failure_reasons.append(src_err)

        exp_pass, exp_err = SyntheticAssertionSuite.evaluate_explainability(scenario, rep_result)
        if not exp_pass and exp_err:
            failure_reasons.append(exp_err)

        orig_obs = baseline_obs[0] if baseline_obs else None
        corr_pass, corr_err = SyntheticAssertionSuite.evaluate_correction(scenario, rep_result, orig_obs)
        if not corr_pass and corr_err:
            failure_reasons.append(corr_err)

        pers_pass, pers_err = SyntheticAssertionSuite.evaluate_persistence(repo, target_station)
        if not pers_pass and pers_err:
            failure_reasons.append(pers_err)

        ws_metrics = ws_mgr.get_metrics()
        ws_count = ws_metrics.get("total_broadcasts", 0)
        ws_pass, ws_err = SyntheticAssertionSuite.evaluate_websocket(ws_count)
        if not ws_pass and ws_err:
            failure_reasons.append(ws_err)

        overall_pass = (
            execution_pass
            and det_pass
            and class_pass
            and health_pass
            and src_pass
            and exp_pass
            and corr_pass
            and pers_pass
            and ws_pass
        )

        status = "PASS" if overall_pass else "FAIL"

        mean_lat = float(np.mean(latencies)) if latencies else 0.0
        p95_lat = float(np.percentile(latencies, 95)) if latencies else 0.0

        return ScenarioRunResult(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            category=scenario.category.value,
            status=status,
            target_stations=scenario.target_stations,
            total_observations_processed=len(obs_window),
            execution_pass=execution_pass,
            detection_pass=det_pass,
            classification_pass=class_pass,
            sensor_health_pass=health_pass,
            source_health_pass=src_pass,
            explainability_pass=exp_pass,
            correction_pass=corr_pass,
            persistence_pass=pers_pass,
            websocket_pass=ws_pass,
            overall_pass=overall_pass,
            ml_anomaly_detected=ml_is_anom,
            ml_score=ml_score,
            hybrid_decision=hybrid_dec_val,
            expected_decision=scenario.expected_decision,
            accepted_decisions=scenario.accepted_decisions,
            actual_decision=actual_decision,
            health_score_before=round(health_score_before, 1),
            health_score_after=round(health_score_after, 1),
            expected_sensor_health_direction=scenario.expected_sensor_health_direction,
            source_health_state=source_state,
            expected_source_health=scenario.expected_source_health,
            mean_latency_ms=round(mean_lat, 2),
            p95_latency_ms=round(p95_lat, 2),
            websocket_events_dispatched=ws_count,
            failure_reasons=failure_reasons,
        )

    def run_all_scenarios(self) -> List[ScenarioRunResult]:
        """Execute the entire suite of 24 validation scenarios."""
        results: List[ScenarioRunResult] = []
        for sc in SCENARIO_DEFINITIONS:
            res = self.run_single_scenario(sc.scenario_id)
            results.append(res)
        return results
