"""Master Explainability and Anomaly Investigation Engine for SkyGuard AI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionReasonCode,
    DecisionSeverity,
    EvidenceState,
    HybridDecision,
    HybridDecisionType,
    MultivariateEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.explainability.episode_reconstructor import AnomalyEpisodeReconstructor
from ml.explainability.neighbor_comparator import NeighborComparator
from ml.explainability.schema import (
    AnomalyEpisode,
    AuditMetadata,
    EvidenceHierarchy,
    ExplanationSummary,
    FeatureContribution,
    NeighborComparison,
)
from ml.explainability.shap_explainer import TreeShapExplainer
from ml.explainability.synthesizer import ExplanationSynthesizer
from ml.models.base import BaseAnomalyModel


class ExplainabilityEngine:
    """Master explainability coordinator for producing auditable, evidence-backed anomaly investigations."""

    def __init__(
        self,
        model: Optional[BaseAnomalyModel] = None,
        feature_version: str = "v1.0.0",
        decision_engine_version: str = "hybrid_v1.0.0",
        explanation_engine_version: str = "xai_v1.0.0",
        top_k_features: int = 5,
    ) -> None:
        """Initialize ExplainabilityEngine.
        
        Args:
            model: Optional fitted anomaly detector model instance.
            feature_version: Identifier of feature pipeline.
            decision_engine_version: Version of hybrid decision engine.
            explanation_engine_version: Version of explainability engine.
            top_k_features: Number of top feature contributions to highlight.
        """
        self.model = model
        self.feature_version = feature_version
        self.decision_engine_version = decision_engine_version
        self.explanation_engine_version = explanation_engine_version
        self.top_k_features = top_k_features

        self.shap_explainer: Optional[TreeShapExplainer] = (
            TreeShapExplainer(model) if model is not None else None
        )
        self.neighbor_comparator = NeighborComparator()
        self.episode_reconstructor = AnomalyEpisodeReconstructor()
        self.synthesizer = ExplanationSynthesizer()

    def set_model(self, model: BaseAnomalyModel) -> None:
        """Set or update the active anomaly detection model for SHAP attribution."""
        self.model = model
        self.shap_explainer = TreeShapExplainer(model)

    def explain(
        self,
        decision: HybridDecision,
        feature_vector: Optional[Union[pd.DataFrame, pd.Series, Dict[str, Any]]] = None,
        neighbor_data: Optional[Union[Dict[str, Optional[float]], pd.DataFrame]] = None,
        target_variable: str = "temperature_c",
        target_value: Optional[float] = None,
        direct_values: Optional[Dict[str, Any]] = None,
    ) -> ExplanationSummary:
        """Generate complete, auditable ExplanationSummary for a given hybrid decision.
        
        Args:
            decision: Completed `HybridDecision` output from `HybridDecisionEngine`.
            feature_vector: Input feature vector evaluated by ML model.
            neighbor_data: Dict of neighbor IDs to values, or DataFrame of neighbor records.
            target_variable: Primary variable investigated (default 'temperature_c').
            target_value: Target station reading.
            direct_values: Additional direct physical measurements.
            
        Returns:
            `ExplanationSummary` object.
        """
        # 1. Compute ML Feature Contributions via TreeSHAP or Fallback
        contributions: List[FeatureContribution] = []
        explanation_method = "UNAVAILABLE"
        if feature_vector is not None and self.shap_explainer is not None:
            contributions = self.shap_explainer.explain_sample(
                sample=feature_vector,
                top_k=self.top_k_features,
            )
            explanation_method = self.shap_explainer.method_tag

        # 2. Compute Neighbor Comparison
        neighbor_comp: Optional[NeighborComparison] = None
        if neighbor_data is not None:
            neighbor_comp = self.neighbor_comparator.compare_neighbors(
                target_station_id=decision.station_id,
                target_timestamp=decision.timestamp,
                target_variable=target_variable,
                target_value=target_value,
                neighbor_data=neighbor_data,
            )

        # 3. Build 4-Tier Evidence Hierarchy
        evidence_hierarchy = self.synthesizer.build_evidence_hierarchy(
            decision=decision,
            contributions=contributions,
            neighbor_comparison=neighbor_comp,
            direct_values=direct_values,
        )

        # 4. Synthesize Deterministic Operator Summary
        summary = self.synthesizer.synthesize_summary(
            decision=decision,
            contributions=contributions,
            neighbor_comp=neighbor_comp,
        )

        # 5. Generate Prioritized Investigation SOP Steps
        investigation_steps = self.synthesizer.generate_investigation_steps(decision=decision)

        # 6. Build Audit Metadata
        audit_metadata = AuditMetadata(
            model_version=decision.evidence.ml_anomaly.model_version,
            feature_version=self.feature_version,
            decision_engine_version=self.decision_engine_version,
            explanation_engine_version=self.explanation_engine_version,
            explanation_method=explanation_method,
            input_station_id=decision.station_id,
            input_timestamp=decision.timestamp,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        return ExplanationSummary(
            station_id=decision.station_id,
            timestamp=decision.timestamp,
            decision=decision.decision,
            severity=decision.severity,
            summary=summary,
            supporting_evidence=list(decision.explanation.supporting_evidence),
            contradicting_evidence=list(decision.explanation.contradicting_evidence),
            unavailable_evidence=list(decision.explanation.unavailable_evidence),
            feature_contributions=contributions,
            spatial_evidence=decision.evidence.spatial,
            temporal_evidence=decision.evidence.temporal,
            data_quality_evidence=decision.evidence.data_quality,
            multivariate_evidence=decision.evidence.multivariate,
            evidence_hierarchy=evidence_hierarchy,
            neighbor_comparison=neighbor_comp,
            recommended_investigation_steps=investigation_steps,
            audit_metadata=audit_metadata,
        )

    def reconstruct_episode(
        self,
        station_id: str,
        event_timestamp: str,
        history_df: pd.DataFrame,
        target_variable: str = "temperature_c",
        score_column: str = "normalized_anomaly_score",
        decision_column: str = "decision",
        neighbor_df: Optional[pd.DataFrame] = None,
    ) -> AnomalyEpisode:
        """Reconstruct anomaly timeline from history."""
        return self.episode_reconstructor.reconstruct_episode(
            station_id=station_id,
            event_timestamp=event_timestamp,
            history_df=history_df,
            target_variable=target_variable,
            score_column=score_column,
            decision_column=decision_column,
            neighbor_df=neighbor_df,
        )
