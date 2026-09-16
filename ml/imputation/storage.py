"""Non-destructive storage and audit persistence layer for SkyGuard AI corrections and imputations."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Sequence, Union

from ml.imputation.schema import (
    CorrectionRecommendation,
    ImputationRecord,
    MultivariateCorrectionBundle,
)


class CorrectionStorageManager:
    """Manages appending and querying non-destructive correction and imputation audit files.
    
    Strict invariant: Never writes to or modifies data/raw/.
    """

    def __init__(self, storage_dir: Union[str, Path] = "data/corrections") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.imputations_file = self.storage_dir / "imputation_records.jsonl"
        self.recommendations_file = self.storage_dir / "correction_recommendations.jsonl"
        self.bundles_file = self.storage_dir / "multivariate_bundles.jsonl"

    def save_imputation_record(self, record: ImputationRecord) -> None:
        """Append an ImputationRecord to JSONL storage."""
        with open(self.imputations_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.model_dump(), default=str) + "\n")

    def save_imputation_records(self, records: Sequence[ImputationRecord]) -> None:
        """Batch append ImputationRecords."""
        with open(self.imputations_file, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.model_dump(), default=str) + "\n")

    def save_correction_recommendation(self, recommendation: CorrectionRecommendation) -> None:
        """Append a CorrectionRecommendation to JSONL storage."""
        with open(self.recommendations_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(recommendation.model_dump(), default=str) + "\n")

    def save_correction_recommendations(self, recommendations: Sequence[CorrectionRecommendation]) -> None:
        """Batch append CorrectionRecommendations."""
        with open(self.recommendations_file, "a", encoding="utf-8") as f:
            for rec in recommendations:
                f.write(json.dumps(rec.model_dump(), default=str) + "\n")

    def save_multivariate_bundle(self, bundle: MultivariateCorrectionBundle) -> None:
        """Append a MultivariateCorrectionBundle to JSONL storage."""
        with open(self.bundles_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(bundle.model_dump(), default=str) + "\n")

    def load_imputation_records(self, station_id: Optional[str] = None) -> List[dict]:
        """Read imputation records, optionally filtered by station."""
        if not self.imputations_file.exists():
            return []
        results = []
        with open(self.imputations_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    if station_id is None or item.get("station_id") == station_id:
                        results.append(item)
        return results

    def load_correction_recommendations(self, station_id: Optional[str] = None) -> List[dict]:
        """Read correction recommendations, optionally filtered by station."""
        if not self.recommendations_file.exists():
            return []
        results = []
        with open(self.recommendations_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    if station_id is None or item.get("station_id") == station_id:
                        results.append(item)
        return results
