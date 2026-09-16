"""Unit tests for ChronologicalSplitter."""

from __future__ import annotations

import pandas as pd
import pytest

from ml.evaluation.splitting import ChronologicalSplitter


def test_chronological_split_by_ratio() -> None:
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=100, freq="1h", tz="UTC")
    df = pd.DataFrame({"timestamp": timestamps, "val": range(100)})

    splitter = ChronologicalSplitter(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
    split_res = splitter.split_by_ratio(df)

    assert len(split_res.train_df) == 60
    assert len(split_res.val_df) == 20
    assert len(split_res.test_df) == 20

    # Assert strictly increasing timestamps across splits (no overlap!)
    t_train_max = split_res.train_df["timestamp"].max()
    t_val_min = split_res.val_df["timestamp"].min()
    t_val_max = split_res.val_df["timestamp"].max()
    t_test_min = split_res.test_df["timestamp"].min()

    assert t_train_max < t_val_min
    assert t_val_max < t_test_min


def test_chronological_split_by_dates() -> None:
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=10, freq="1D", tz="UTC")
    df = pd.DataFrame({"timestamp": timestamps, "val": range(10)})

    splitter = ChronologicalSplitter()
    split_res = splitter.split_by_dates(
        df,
        train_end_cutoff="2024-01-06T00:00:00Z",
        val_end_cutoff="2024-01-08T00:00:00Z",
    )

    assert len(split_res.train_df) == 5  # Jan 1 to Jan 5
    assert len(split_res.val_df) == 2    # Jan 6 to Jan 7
    assert len(split_res.test_df) == 3   # Jan 8 to Jan 10
