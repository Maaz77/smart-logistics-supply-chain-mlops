"""Tests for the ML pipeline."""

from pathlib import Path

import pandas as pd
import pytest


class TestTimeSplit:
    """Tests for time-based data splitting."""

    @pytest.fixture
    def processed_data_dir(self):
        """Return processed data directory path."""
        return Path("data/processed")

    def test_time_split_no_leakage(self, processed_data_dir):
        """Verify that train timestamps are before test timestamps (no leakage)."""
        train_path = processed_data_dir / "train.parquet"
        val_path = processed_data_dir / "val.parquet"
        test_path = processed_data_dir / "test.parquet"

        # Skip if files don't exist (pipeline not run yet)
        if not all(p.exists() for p in [train_path, val_path, test_path]):
            pytest.skip("Processed data files not found. Run 'make pipeline' first.")

        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)
        test_df = pd.read_parquet(test_path)

        # Convert Timestamp if it's still a string
        for df in [train_df, val_df, test_df]:
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"])

        # Verify chronological ordering
        if "Timestamp" in train_df.columns:
            train_max = train_df["Timestamp"].max()
            val_min = val_df["Timestamp"].min()
            val_max = val_df["Timestamp"].max()
            test_min = test_df["Timestamp"].min()

            assert (
                train_max < val_min
            ), f"Data leakage: train max ({train_max}) >= val min ({val_min})"
            assert (
                val_max < test_min
            ), f"Data leakage: val max ({val_max}) >= test min ({test_min})"

    def test_split_ratios(self, processed_data_dir):
        """Verify approximate split ratios (70/15/15)."""
        train_path = processed_data_dir / "train.parquet"
        val_path = processed_data_dir / "val.parquet"
        test_path = processed_data_dir / "test.parquet"

        if not all(p.exists() for p in [train_path, val_path, test_path]):
            pytest.skip("Processed data files not found. Run 'make pipeline' first.")

        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)
        test_df = pd.read_parquet(test_path)

        total = len(train_df) + len(val_df) + len(test_df)
        train_ratio = len(train_df) / total
        val_ratio = len(val_df) / total
        test_ratio = len(test_df) / total

        # Allow 2% tolerance
        assert (
            0.68 <= train_ratio <= 0.72
        ), f"Train ratio {train_ratio:.2%} not in [68%, 72%]"
        assert 0.13 <= val_ratio <= 0.17, f"Val ratio {val_ratio:.2%} not in [13%, 17%]"
        assert (
            0.13 <= test_ratio <= 0.17
        ), f"Test ratio {test_ratio:.2%} not in [13%, 17%]"

    def test_expected_columns_exist(self, processed_data_dir):
        """Verify expected feature columns exist in processed data."""
        train_path = processed_data_dir / "train.parquet"

        if not train_path.exists():
            pytest.skip("Processed data files not found. Run 'make pipeline' first.")

        train_df = pd.read_parquet(train_path)

        # Expected temporal features
        expected_features = ["hour", "day_of_week", "month"]
        for col in expected_features:
            assert col in train_df.columns, f"Missing expected feature: {col}"

        # Target column
        assert (
            "Logistics_Delay" in train_df.columns
        ), "Missing target column: Logistics_Delay"
