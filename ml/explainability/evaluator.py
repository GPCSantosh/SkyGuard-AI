"""Semantic evaluation suite for validating explanation quality against synthetic anomaly classes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
from ml.explainability.schema import ExplanationSummary


class ExplanationSemanticEvaluator:
    """Evaluates whether generated explanations accurately reflect the underlying physical and statistical anomaly type."""

    # Semantic keyword patterns per anomaly category
    KEYWORD_MAPPINGS = {
        "SPIKE": ["rate", "rapid", "spike", "departure", "deviat", "abnormal", "excess"],
        "FROZEN_SENSOR": ["unchanged", "persist", "flatline", "stuck", "zero variance", "freez"],
        "DRIFT": ["deviat", "depart", "drift", "offset", "anomaly", "residual"],
        "LOCAL_SENSOR_FAULT": ["isolated", "single-station", "stable", "contradict", "not corroborate", "excess"],
        "REGIONAL_EVENT": ["regional", "corroborat", "stations", "network", "meso-scale", "cluster", "consistent with a regional event"],
        "DATA_GAP": ["gap", "missing", "telemetry", "communication", "packet", "defect"],
        "PHYSICAL_LIMIT": ["physical", "planetary", "limit", "bound", "breach", "thermodynamic"],
        "MULTIVARIATE_FAULT": ["multivariate", "thermodynamic", "humidity", "dew point", "august-roche-magnus", "inconsistent"],
    }

    def __init__(self) -> None:
        pass

    def evaluate_explanation_semantics(
        self,
        explanation: ExplanationSummary,
        expected_anomaly_type: str,
    ) -> Dict[str, Any]:
        """Verify that explanation text and evidence contain semantic signatures of the anomaly.
        
        Args:
            explanation: Generated `ExplanationSummary`.
            expected_anomaly_type: Standardized anomaly category (e.g. 'SPIKE', 'FROZEN_SENSOR', 'REGIONAL_EVENT').
            
        Returns:
            Dict containing `passed` bool, `matched_keywords`, and `score`.
        """
        category_key = expected_anomaly_type.upper().replace(" ", "_")
        
        # Normalize category
        if "SPIKE" in category_key:
            category_key = "SPIKE"
        elif "FROZEN" in category_key or "FLATLINE" in category_key or "STUCK" in category_key:
            category_key = "FROZEN_SENSOR"
        elif "DRIFT" in category_key or "OFFSET" in category_key:
            category_key = "DRIFT"
        elif "REGIONAL" in category_key or "SQUALL" in category_key:
            category_key = "REGIONAL_EVENT"
        elif "GAP" in category_key or "MISSING" in category_key:
            category_key = "DATA_GAP"
        elif "PHYSICAL" in category_key or "OUT_OF_BOUNDS" in category_key:
            category_key = "PHYSICAL_LIMIT"
        elif "MULTIVARIATE" in category_key or "INCONSISTENCY" in category_key:
            category_key = "MULTIVARIATE_FAULT"

        expected_keywords = self.KEYWORD_MAPPINGS.get(category_key, ["anomaly", "deviat"])

        # Aggregate text across explanation fields
        text_corpus = " ".join([
            explanation.summary.lower(),
            " ".join(explanation.supporting_evidence).lower(),
            " ".join(explanation.contradicting_evidence).lower(),
            " ".join(explanation.recommended_investigation_steps).lower(),
            str(explanation.evidence_hierarchy.model_dump()).lower(),
        ])

        matched = [kw for kw in expected_keywords if kw.lower() in text_corpus]
        passed = len(matched) > 0

        return {
            "expected_category": category_key,
            "passed": passed,
            "matched_keywords": matched,
            "missing_keywords": [kw for kw in expected_keywords if kw not in matched],
            "explanation_summary": explanation.summary,
        }

    def evaluate_batch(
        self,
        test_cases: Sequence[Tuple[ExplanationSummary, str]],
    ) -> Dict[str, Any]:
        """Evaluate a batch of explanation test cases and return aggregate pass rate."""
        results = [self.evaluate_explanation_semantics(exp, cat) for exp, cat in test_cases]
        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        pass_rate = (passed_count / total) if total > 0 else 0.0

        return {
            "total_evaluated": total,
            "passed_count": passed_count,
            "pass_rate": round(pass_rate, 4),
            "all_passed": passed_count == total,
            "detailed_results": results,
        }
