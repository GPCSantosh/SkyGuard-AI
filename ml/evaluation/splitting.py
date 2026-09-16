"""Chronological time-series dataset partitioner for SkyGuard AI."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class DatasetSplitResult(BaseModel):
    """Container holding temporal partitions and boundary metadata."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    train_start: str
    train_end: str
    val_start: str
    val_end: str
    test_start: str
    test_end: str
    total_observations: int

    def summary(self) -> str:
        return (
            f"Temporal Dataset Split Summary:\n"
            f"  Train:      {len(self.train_df):,} rows ({self.train_start} to {self.train_end})\n"
            f"  Validation: {len(self.val_df):,} rows ({self.val_start} to {self.val_end})\n"
            f"  Test:       {len(self.test_df):,} rows ({self.test_start} to {self.test_end})\n"
            f"  Total:      {self.total_observations:,} rows"
        )


class ChronologicalSplitter:
    """Partitions time series strictly along chronological boundaries to prevent lookahead data leakage."""

    def __init__(
        self,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        test_ratio: float = 0.2,
        timestamp_col: str = "timestamp",
    ) -> None:
        if not abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5:
            raise ValueError("Split ratios must sum to 1.0")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.timestamp_col = timestamp_col

    def split_by_ratio(self, df: pd.DataFrame) -> DatasetSplitResult:
        """Split DataFrame into Train/Val/Test by chronological proportions."""
        if df.empty:
            raise ValueError("Cannot split empty DataFrame.")

        df_sorted = df.sort_values(by=self.timestamp_col).reset_index(drop=True)
        n = len(df_sorted)

        train_end_idx = max(1, int(n * self.train_ratio))
        val_end_idx = max(train_end_idx + 1, int(n * (self.train_ratio + self.val_ratio)))
        val_end_idx = min(val_end_idx, n - 1) if n > 2 else n

        train_df = df_sorted.iloc[:train_end_idx].copy()
        val_df = df_sorted.iloc[train_end_idx:val_end_idx].copy()
        test_df = df_sorted.iloc[val_end_idx:].copy()

        # Handle edge cases where dataset is very small
        if val_df.empty:
            val_df = train_df.tail(1).copy()
        if test_df.empty:
            test_df = val_df.tail(1).copy()

        return DatasetSplitResult(
            train_df=train_df,
            val_df=val_df,
            test_df=test_df,
            train_start=str(train_df[self.timestamp_col].min()),
            train_end=str(train_df[self.timestamp_col].max()),
            val_start=str(val_df[self.timestamp_col].min()),
            val_end=str(val_df[self.timestamp_col].max()),
            test_start=str(test_df[self.timestamp_col].min()),
            test_end=str(test_df[self.timestamp_col].max()),
            total_observations=n,
        )

    def split_by_dates(
        self,
        df: pd.DataFrame,
        train_end_cutoff: Union[str, pd.Timestamp],
        val_end_cutoff: Union[str, pd.Timestamp],
    ) -> DatasetSplitResult:
        """Split DataFrame by explicit timestamp cutoffs."""
        df_sorted = df.sort_values(by=self.timestamp_col).reset_index(drop=True)
        t_col = pd.to_datetime(df_sorted[self.timestamp_col], utc=True)
        t1 = pd.to_datetime(train_end_cutoff, utc=True)
        t2 = pd.to_datetime(val_end_cutoff, utc=True)

        train_df = df_sorted[t_col < t1].copy()
        val_df = df_sorted[(t_col >= t1) & (t_col < t2)].copy()
        test_df = df_sorted[t_col >= t2].copy()

        return DatasetSplitResult(
            train_df=train_df,
            val_df=val_df,
            test_df=test_df,
            train_start=str(train_df[self.timestamp_col].min()) if not train_df.empty else "N/A",
            train_end=str(train_df[self.timestamp_col].max()) if not train_df.empty else "N/A",
            val_start=str(val_df[self.timestamp_col].min()) if not val_df.empty else "N/A",
            val_end=str(val_df[self.timestamp_col].max()) if not val_df.empty else "N/A",
            test_start=str(test_df[self.timestamp_col].min()) if not test_df.empty else "N/A",
            test_end=str(test_df[self.timestamp_col].max()) if not test_df.empty else "N/A",
            total_observations=len(df_sorted),
        )
