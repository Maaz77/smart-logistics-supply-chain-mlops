"""
Feature Engineering and Preprocessing Module for Smart Logistics Supply Chain.

Reads from S3, processes data, and writes back to S3.
"""

import io
import logging

import pandas as pd
from sklearn.preprocessing import LabelEncoder

from src.ml_pipeline.common import get_data_bucket, get_s3_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
S3_RAW_KEY = "raw/logistics.csv"
S3_PROCESSED_PREFIX = "processed"

# Split ratios (time-based)
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Categorical columns to encode
CATEGORICAL_COLUMNS = ["Shipment_Status", "Traffic_Status", "Logistics_Delay_Reason"]

# Target column
TARGET_COLUMN = "Logistics_Delay"


def load_raw_data_from_s3() -> pd.DataFrame:
    """Load raw data directly from S3.

    Returns:
        DataFrame with raw logistics data.
    """
    s3_client = get_s3_client()
    bucket = get_data_bucket()

    logger.info(f"Loading raw data from s3://{bucket}/{S3_RAW_KEY}")
    response = s3_client.get_object(Bucket=bucket, Key=S3_RAW_KEY)
    df = pd.read_csv(response["Body"])
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def extract_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract temporal features from Timestamp column.

    Args:
        df: Input DataFrame with Timestamp column.

    Returns:
        DataFrame with added temporal features.
    """
    logger.info("Extracting temporal features from Timestamp")

    # Convert Timestamp to datetime
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    # Extract temporal features
    df["hour"] = df["Timestamp"].dt.hour
    df["day_of_week"] = df["Timestamp"].dt.dayofweek
    df["month"] = df["Timestamp"].dt.month

    logger.info("Added features: hour, day_of_week, month")
    return df


def encode_categorical_columns(
    df: pd.DataFrame, encoders: dict[str, LabelEncoder] | None = None
) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    """Encode categorical columns using LabelEncoder.

    Args:
        df: Input DataFrame.
        encoders: Optional pre-fitted encoders for transform-only mode.

    Returns:
        Tuple of (encoded DataFrame, encoders dict).
    """
    logger.info(f"Encoding categorical columns: {CATEGORICAL_COLUMNS}")

    if encoders is None:
        encoders = {}

    df = df.copy()

    for col in CATEGORICAL_COLUMNS:
        if col not in df.columns:
            logger.warning(f"Column {col} not found in DataFrame, skipping")
            continue

        # Fill NaN values with 'Unknown'
        df[col] = df[col].fillna("Unknown")

        if col not in encoders:
            # Fit new encoder
            encoders[col] = LabelEncoder()
            df[col] = encoders[col].fit_transform(df[col].astype(str))
        else:
            # Use existing encoder
            df[col] = encoders[col].transform(df[col].astype(str))

    return df, encoders


def time_based_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split data chronologically to prevent data leakage.

    Sorts by Timestamp and splits:
    - First 70% -> train
    - Next 15% -> validation
    - Last 15% -> test

    Args:
        df: Input DataFrame with Timestamp column.

    Returns:
        Tuple of (train_df, val_df, test_df).
    """
    logger.info("Performing time-based train/val/test split")

    # Sort by timestamp
    df_sorted = df.sort_values("Timestamp").reset_index(drop=True)
    n = len(df_sorted)

    # Calculate split indices
    train_end = int(n * TRAIN_RATIO)
    val_end = int(n * (TRAIN_RATIO + VAL_RATIO))

    # Split
    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    logger.info(
        f"Split sizes - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}"
    )

    # Verify no data leakage
    train_max_ts = train_df["Timestamp"].max()
    val_min_ts = val_df["Timestamp"].min()
    test_min_ts = test_df["Timestamp"].min()

    assert train_max_ts < val_min_ts, "Data leakage: train overlaps with val"
    assert (
        val_df["Timestamp"].max() < test_min_ts
    ), "Data leakage: val overlaps with test"
    logger.info("✓ Verified no data leakage between splits")

    return train_df, val_df, test_df


def upload_dataframe_to_s3(df: pd.DataFrame, s3_key: str) -> str:
    """Upload DataFrame directly to S3 as parquet.

    Args:
        df: DataFrame to upload.
        s3_key: S3 key for the file.

    Returns:
        S3 URI of the uploaded file.
    """
    s3_client = get_s3_client()
    bucket = get_data_bucket()

    # Convert DataFrame to parquet bytes
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    logger.info(f"Uploading to s3://{bucket}/{s3_key}")
    s3_client.put_object(Bucket=bucket, Key=s3_key, Body=buffer.getvalue())

    return f"s3://{bucket}/{s3_key}"


def run_preprocessing() -> dict:
    """Run the full preprocessing pipeline.

    Reads from S3, processes data, and writes back to S3.

    Returns:
        Dictionary with preprocessing results.
    """
    logger.info("=" * 50)
    logger.info("Starting Feature Engineering Pipeline")
    logger.info("=" * 50)

    # Step 1: Load raw data from S3
    df = load_raw_data_from_s3()

    # Step 2: Extract temporal features
    df = extract_temporal_features(df)

    # Step 3: Time-based split (before encoding to avoid leakage)
    train_df, val_df, test_df = time_based_split(df)

    # Step 4: Encode categorical columns (fit on train, transform all)
    train_df, encoders = encode_categorical_columns(train_df)
    val_df, _ = encode_categorical_columns(val_df, encoders)
    test_df, _ = encode_categorical_columns(test_df, encoders)

    # Step 5: Upload directly to S3
    s3_uris = {}
    for name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        s3_key = f"{S3_PROCESSED_PREFIX}/{name}.parquet"
        s3_uris[name] = upload_dataframe_to_s3(split_df, s3_key)

    result = {
        "s3_uris": s3_uris,
        "train_size": len(train_df),
        "val_size": len(val_df),
        "test_size": len(test_df),
        "status": "success",
    }

    logger.info("=" * 50)
    logger.info("Feature Engineering Complete!")
    logger.info(f"  Train: {len(train_df)} rows -> {s3_uris['train']}")
    logger.info(f"  Val: {len(val_df)} rows -> {s3_uris['val']}")
    logger.info(f"  Test: {len(test_df)} rows -> {s3_uris['test']}")
    logger.info("=" * 50)

    return result


if __name__ == "__main__":
    run_preprocessing()
