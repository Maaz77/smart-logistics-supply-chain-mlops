"""
Model Monitoring Module for Smart Logistics Supply Chain.

Simulates production monitoring by calculating Evidently metrics
on validation data day-by-day and logging them to PostgreSQL.
"""

import io
import logging
import os
import time
import warnings
from datetime import date, datetime

import mlflow
import numpy as np
import pandas as pd
import psycopg2
from evidently import ColumnMapping
from evidently.metrics import (
    ColumnDriftMetric,
    DatasetDriftMetric,
    DatasetMissingValuesMetric,
)
from evidently.report import Report

from src.ml_pipeline.common import (
    get_data_bucket,
    get_mlflow_tracking_uri,
    get_s3_client,
)

# Suppress NumPy warnings for cleaner output (common with small datasets)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
S3_PROCESSED_PREFIX = "processed"
MONITORING_DB = "monitoring"
MONITORING_TABLE = "monitoring_metrics"
PAUSE_SECONDS = 5  # Pause between days
MODEL_NAME = "LogisticsDelayModel"  # MLflow registered model name
TARGET_COLUMN = "Logistics_Delay"


def get_monitoring_db_connection() -> psycopg2.extensions.connection:
    """Get PostgreSQL connection to monitoring database.

    Returns:
        PostgreSQL connection object.
    """
    import os

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "mlflow")
    password = os.getenv("POSTGRES_PASSWORD", "mlflow")
    database = MONITORING_DB

    conn_str = f"host={host} port={port} user={user} password={password} dbname={database}"
    logger.info(f"Connecting to monitoring database: {host}:{port}/{database}")
    return psycopg2.connect(conn_str)


def create_monitoring_table(conn: psycopg2.extensions.connection) -> None:
    """Create monitoring_metrics table if it doesn't exist.

    The table stores the following metrics:
    - column_drift_score: Average drift score across all numeric columns (0-1, higher = more drift)
    - dataset_drift_score: Overall dataset drift (share of drifted columns, 0-1)
    - missing_values_share: Proportion of missing values in current data (0-1)
    - prediction_drift_score: Drift in model predictions (0-1, higher = more drift)

    Args:
        conn: PostgreSQL connection object.
    """
    with conn.cursor() as cur:
        # Check if prediction_drift_score column exists, add it if not
        cur.execute(
            f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='{MONITORING_TABLE}' AND column_name='prediction_drift_score'
            """
        )
        has_prediction_drift = cur.fetchone() is not None

        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {MONITORING_TABLE} (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                date DATE NOT NULL,
                column_drift_score NUMERIC,
                dataset_drift_score NUMERIC,
                missing_values_share NUMERIC,
                prediction_drift_score NUMERIC,
                metric_details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Add prediction_drift_score column if table exists but column doesn't
        if not has_prediction_drift:
            try:
                cur.execute(
                    f"ALTER TABLE {MONITORING_TABLE} ADD COLUMN prediction_drift_score NUMERIC"
                )
                logger.info("✓ Added prediction_drift_score column to existing table")
            except Exception as e:
                logger.debug(f"Column may already exist: {e}")

        conn.commit()
        logger.info(f"✓ Table '{MONITORING_TABLE}' is ready")


def load_dataframe_from_s3(s3_key: str) -> pd.DataFrame:
    """Load DataFrame from S3 parquet file.

    Args:
        s3_key: S3 key for the parquet file.

    Returns:
        DataFrame loaded from S3.
    """
    s3_client = get_s3_client()
    bucket = get_data_bucket()

    logger.info(f"Loading from s3://{bucket}/{s3_key}")
    response = s3_client.get_object(Bucket=bucket, Key=s3_key)
    df = pd.read_parquet(io.BytesIO(response["Body"].read()))
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def prepare_data_for_monitoring(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for monitoring by ensuring Timestamp is datetime.

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with Timestamp as datetime.
    """
    df = df.copy()
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    """Get list of numeric column names.

    Args:
        df: Input DataFrame.

    Returns:
        List of numeric column names.
    """
    numeric_cols = df.select_dtypes(
        include=["int64", "float64", "int32", "float32"]
    ).columns.tolist()
    # Exclude target column if present
    if "Logistics_Delay" in numeric_cols:
        numeric_cols.remove("Logistics_Delay")
    return numeric_cols


def load_model_from_mlflow() -> object:
    """Load the latest production model from MLflow model registry.

    Returns:
        Loaded MLflow model (sklearn model).
    """
    tracking_uri = get_mlflow_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)

    # Set S3 endpoint for artifact storage
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = os.getenv(
        "AWS_ENDPOINT_URL", "http://localhost:4566"
    )
    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "test")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

    logger.info(f"Loading model '{MODEL_NAME}' from MLflow...")
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/latest")
    logger.info("✓ Model loaded successfully")
    return model


def prepare_features_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare features for model prediction (same as training pipeline).

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with features ready for prediction.
    """
    # Drop non-feature columns (same logic as training)
    drop_cols = ["Timestamp", TARGET_COLUMN]
    cols_to_drop = [col for col in drop_cols if col in df.columns]

    X = df.drop(columns=cols_to_drop, errors="ignore")

    # Keep only numeric columns
    numeric_cols = X.select_dtypes(
        include=["int64", "float64", "int32", "float32"]
    ).columns
    X = X[numeric_cols]

    return X


def calculate_evidently_metrics(
    reference_data: pd.DataFrame, current_data: pd.DataFrame, model: object | None = None
) -> dict:
    """Calculate Evidently metrics comparing current to reference data.

    METRICS EXPLANATION:
    --------------------
    1. **column_drift_score** (Average, 0-1):
       - What it means: Average statistical drift across all numeric feature columns
       - How calculated: For each numeric column, Evidently performs statistical tests
         (KS test, Chi-square, etc.) to compare reference vs current distributions.
         Returns p-value (0-1). Lower p-value = more drift detected.
         We convert: drift_score = 1 - p_value (so higher = more drift).
       - Interpretation:
         - 0.0-0.3: Low drift (data similar to training)
         - 0.3-0.7: Moderate drift (some changes detected)
         - 0.7-1.0: High drift (significant distribution changes)

    2. **dataset_drift_score** (0-1):
       - What it means: Overall dataset-level drift (proportion of columns that drifted)
       - How calculated: Evidently checks all numeric columns for drift, counts how many
         show significant drift (p < threshold, typically 0.05), then calculates:
         drift_score = number_of_drifted_columns / total_columns
       - Interpretation:
         - 0.0: No columns drifted (data very similar to training)
         - 0.0-0.3: Few columns drifted (mostly stable)
         - 0.3-0.7: Many columns drifted (moderate changes)
         - 0.7-1.0: Most/all columns drifted (major distribution shift)

    3. **missing_values_share** (0-1):
       - What it means: Proportion of missing/null values in the current dataset
       - How calculated: Counts all NaN/null values across all columns, divides by
         total cells: missing_share = total_missing_cells / (rows × columns)
       - Interpretation:
         - 0.0: No missing values (data complete)
         - 0.0-0.1: Few missing values (acceptable)
         - 0.1-0.3: Moderate missing values (may need attention)
         - >0.3: High missing values (data quality issue)

    4. **prediction_drift_score** (0-1):
       - What it means: Drift in model predictions (how predictions differ from training)
       - How calculated: Generates predictions on both reference and current data,
         compares prediction distributions using statistical tests (KS test).
         Returns p-value, converted to drift score: 1 - p_value
       - Interpretation:
         - 0.0-0.3: Predictions stable (model behavior consistent)
         - 0.3-0.7: Moderate prediction drift (model outputs changing)
         - 0.7-1.0: High prediction drift (model behavior significantly different)

    Args:
        reference_data: Reference dataset (train set).
        current_data: Current dataset (day batch from validation set).
        model: Optional MLflow model for prediction drift calculation.

    Returns:
        Dictionary with metric values.
    """
    logger.info(f"Calculating metrics: reference={len(reference_data)} rows, current={len(current_data)} rows")

    # Get numeric columns for drift detection
    numeric_columns = get_numeric_columns(reference_data)

    # Prepare data copies for prediction drift (if model provided)
    reference_data_with_pred = reference_data.copy()
    current_data_with_pred = current_data.copy()
    has_predictions = False

    # Generate predictions if model is provided
    if model is not None:
        try:
            # Prepare features
            X_ref = prepare_features_for_prediction(reference_data)
            X_curr = prepare_features_for_prediction(current_data)

            # Generate predictions
            logger.info("Generating predictions for drift detection...")
            ref_predictions = model.predict_proba(X_ref)[:, 1]  # Probability of class 1
            curr_predictions = model.predict_proba(X_curr)[:, 1]

            # Add predictions as columns
            reference_data_with_pred["prediction"] = ref_predictions
            current_data_with_pred["prediction"] = curr_predictions
            has_predictions = True
            logger.info("✓ Predictions generated")
        except Exception as e:
            logger.warning(f"Could not generate predictions: {e}, skipping prediction drift")
            has_predictions = False

    # Create column mapping
    column_mapping = ColumnMapping(
        numerical_features=numeric_columns,
        target=None,  # No target for drift detection
        prediction="prediction" if has_predictions else None,
    )

    # Create metrics
    metrics = [
        DatasetDriftMetric(),
        DatasetMissingValuesMetric(),
    ]

    # Add column drift metrics for each numeric column
    for col in numeric_columns:
        if col in reference_data.columns and col in current_data.columns:
            metrics.append(ColumnDriftMetric(column_name=col))

    # Add prediction drift metric if we have predictions
    # We use ColumnDriftMetric on the prediction column to measure prediction drift
    if has_predictions:
        metrics.append(ColumnDriftMetric(column_name="prediction"))

    # Create and run report
    report = Report(metrics=metrics)
    report.run(
        reference_data=reference_data_with_pred,
        current_data=current_data_with_pred,
        column_mapping=column_mapping,
    )

    # Extract metric results
    results = report.as_dict()

    # Extract specific metric values
    metrics_dict = {
        "dataset_drift_score": None,
        "missing_values_share": None,
        "prediction_drift_score": None,
        "column_drift_scores": {},
    }

    # Parse metrics from dictionary structure (Evidently's as_dict() format)
    metrics_list = results.get("metrics", [])

    # Debug: log the structure if needed
    if not metrics_list:
        logger.debug(f"Report structure keys: {list(results.keys())}")
        # Try alternative structure
        metrics_list = results.get("metric_results", [])

    # Parse each metric from the list
    for metric_result in metrics_list:
        if not isinstance(metric_result, dict):
            continue

        # Extract metric name and result data
        metric_name = metric_result.get("metric", "") or metric_result.get("metric_name", "")
        metric_result_data = metric_result.get("result", {}) or metric_result.get("metric_result", {})

        if not metric_result_data or not isinstance(metric_result_data, dict):
            continue

        # Parse DatasetDriftMetric
        if "DatasetDriftMetric" in metric_name:
            # Try multiple possible keys for drift score
            # Evidently returns share_of_drifted_columns as the main metric
            drift_share = metric_result_data.get("share_of_drifted_columns")
            number_drifted = metric_result_data.get("number_of_drifted_columns")
            number_total = metric_result_data.get("number_of_columns")

            if drift_share is not None:
                try:
                    metrics_dict["dataset_drift_score"] = float(drift_share)
                except (ValueError, TypeError):
                    pass
            elif number_drifted is not None and number_total is not None and number_total > 0:
                try:
                    metrics_dict["dataset_drift_score"] = float(number_drifted) / float(number_total)
                except (ValueError, TypeError):
                    pass

        # Parse DatasetMissingValuesMetric
        elif "DatasetMissingValuesMetric" in metric_name:
            # Get current missing values share
            current_data = metric_result_data.get("current", {})
            if isinstance(current_data, dict):
                missing_share = current_data.get("share_of_missing_values")
                if missing_share is not None:
                    try:
                        metrics_dict["missing_values_share"] = float(missing_share)
                    except (ValueError, TypeError):
                        pass

        # Parse ColumnDriftMetric (including prediction drift)
        elif "ColumnDriftMetric" in metric_name:
            # Get column name and drift score
            column_name = metric_result_data.get("column_name")
            drift_score = metric_result_data.get("drift_score")
            drift_detected = metric_result_data.get("drift_detected")

            if column_name:
                # Check if this is the prediction column
                if column_name == "prediction":
                    # This is prediction drift
                    if drift_score is not None:
                        try:
                            # drift_score is p-value (0-1), lower = more drift
                            # Convert to drift indicator: 1 - p_value (higher = more drift)
                            p_value = float(drift_score)
                            metrics_dict["prediction_drift_score"] = 1.0 - p_value
                        except (ValueError, TypeError):
                            pass
                    elif drift_detected is not None:
                        try:
                            # Boolean: True = drift detected, False = no drift
                            metrics_dict["prediction_drift_score"] = 1.0 if drift_detected else 0.0
                        except (ValueError, TypeError):
                            pass
                else:
                    # This is a regular feature column drift
                    if drift_score is not None:
                        try:
                            # drift_score is p-value (0-1), lower = more drift
                            # Convert to drift indicator: 1 - p_value (higher = more drift)
                            p_value = float(drift_score)
                            metrics_dict["column_drift_scores"][str(column_name)] = 1.0 - p_value
                        except (ValueError, TypeError):
                            pass
                    elif drift_detected is not None:
                        try:
                            # Boolean: True = drift detected, False = no drift
                            metrics_dict["column_drift_scores"][str(column_name)] = 1.0 if drift_detected else 0.0
                        except (ValueError, TypeError):
                            pass
        elif "ColumnDriftMetric" in metric_name:
            # Get column name and drift score
            column_name = metric_result_data.get("column_name")
            drift_score = metric_result_data.get("drift_score")
            drift_detected = metric_result_data.get("drift_detected")

            if column_name:
                # Prefer drift_score (p-value), fall back to drift_detected (boolean)
                if drift_score is not None:
                    try:
                        # drift_score is typically a p-value (0-1), lower = more drift
                        # Convert to drift indicator: 1 - p_value (higher = more drift)
                        p_value = float(drift_score)
                        metrics_dict["column_drift_scores"][str(column_name)] = 1.0 - p_value
                    except (ValueError, TypeError):
                        pass
                elif drift_detected is not None:
                    try:
                        # Boolean: True = drift detected, False = no drift
                        metrics_dict["column_drift_scores"][str(column_name)] = 1.0 if drift_detected else 0.0
                    except (ValueError, TypeError):
                        pass

    # Calculate average column drift score
    if metrics_dict["column_drift_scores"]:
        avg_column_drift = sum(metrics_dict["column_drift_scores"].values()) / len(
            metrics_dict["column_drift_scores"]
        )
        metrics_dict["column_drift_score"] = avg_column_drift
    else:
        metrics_dict["column_drift_score"] = None

    logger.info(
        f"Metrics calculated - Dataset drift: {metrics_dict['dataset_drift_score']}, "
        f"Missing values: {metrics_dict['missing_values_share']}, "
        f"Prediction drift: {metrics_dict['prediction_drift_score']}, "
        f"Avg column drift: {metrics_dict['column_drift_score']}"
    )

    return metrics_dict


def log_metrics_to_db(
    conn: psycopg2.extensions.connection,
    metrics: dict,
    date_str: str,
    timestamp: datetime,
) -> None:
    """Log metrics to PostgreSQL monitoring database.

    Args:
        conn: PostgreSQL connection object.
        metrics: Dictionary with metric values.
        date_str: Date string (YYYY-MM-DD).
        timestamp: Timestamp for the metrics.
    """
    import json

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {MONITORING_TABLE} (
                timestamp, date, column_drift_score, dataset_drift_score,
                missing_values_share, prediction_drift_score, metric_details
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                timestamp,
                date_str,
                metrics.get("column_drift_score"),
                metrics.get("dataset_drift_score"),
                metrics.get("missing_values_share"),
                metrics.get("prediction_drift_score"),
                json.dumps(metrics.get("column_drift_scores", {})),
            ),
        )
        conn.commit()
        logger.info(f"✓ Logged metrics for {date_str} to database")


def run_monitoring() -> dict:
    """Run the full monitoring simulation.

    Processes validation data day-by-day, calculates Evidently metrics,
    and logs them to PostgreSQL with 20-second pauses between days.

    Returns:
        Dictionary with monitoring results.
    """
    logger.info("=" * 50)
    logger.info("Starting Model Monitoring Simulation")
    logger.info("=" * 50)

    # Step 1: Load reference data (train set)
    logger.info("Step 1: Loading reference data (train set)...")
    reference_df = load_dataframe_from_s3(f"{S3_PROCESSED_PREFIX}/train.parquet")
    reference_df = prepare_data_for_monitoring(reference_df)
    logger.info(f"✓ Reference data loaded: {len(reference_df)} rows")

    # Step 2: Load current data (validation set)
    logger.info("Step 2: Loading current data (validation set)...")
    current_df = load_dataframe_from_s3(f"{S3_PROCESSED_PREFIX}/val.parquet")
    current_df = prepare_data_for_monitoring(current_df)
    logger.info(f"✓ Current data loaded: {len(current_df)} rows")

    # Step 3: Load model for prediction drift
    logger.info("Step 3: Loading model from MLflow for prediction drift...")
    try:
        model = load_model_from_mlflow()
    except Exception as e:
        logger.warning(f"Could not load model: {e}, continuing without prediction drift")
        model = None

    # Step 4: Ensure Timestamp column exists
    if "Timestamp" not in current_df.columns:
        raise ValueError("Timestamp column not found in validation data")

    # Step 5: Group validation data by day
    current_df["date"] = pd.to_datetime(current_df["Timestamp"]).dt.date
    unique_dates = sorted(current_df["date"].unique())
    logger.info(f"Found {len(unique_dates)} unique days in validation data")
    logger.info(f"Date range: {min(unique_dates)} to {max(unique_dates)}")

    # Step 6: Connect to monitoring database
    logger.info("Step 4: Connecting to monitoring database...")
    conn = get_monitoring_db_connection()
    create_monitoring_table(conn)
    logger.info("✓ Database connection ready")

    # Step 6: Process each day
    results = {
        "total_days": len(unique_dates),
        "processed_days": 0,
        "failed_days": 0,
        "dates_processed": [],
    }

    logger.info("=" * 50)
    logger.info("Starting day-by-day monitoring simulation...")
    logger.info("=" * 50)

    for idx, day_date in enumerate(unique_dates, 1):
        date_str = day_date.strftime("%Y-%m-%d")
        logger.info("")
        logger.info(f"[{idx}/{len(unique_dates)}] Processing {date_str}...")

        try:
            # Filter data for this day
            day_data = current_df[current_df["date"] == day_date].copy()
            day_data = day_data.drop(columns=["date"], errors="ignore")

            if len(day_data) == 0:
                logger.warning(f"No data found for {date_str}, skipping...")
                continue

            logger.info(f"  Rows for {date_str}: {len(day_data)}")

            # Calculate metrics
            metrics = calculate_evidently_metrics(reference_df, day_data, model)

            # Log to database
            timestamp = datetime.now()
            log_metrics_to_db(conn, metrics, date_str, timestamp)

            results["processed_days"] += 1
            results["dates_processed"].append(date_str)

            logger.info(f"✓ Completed {date_str}")

            # Pause before next day (except for the last day)
            if idx < len(unique_dates):
                logger.info(f"  Pausing {PAUSE_SECONDS} seconds before next day...")
                time.sleep(PAUSE_SECONDS)

        except Exception as e:
            logger.error(f"✗ Error processing {date_str}: {str(e)}", exc_info=True)
            results["failed_days"] += 1

    # Close database connection
    conn.close()

    logger.info("")
    logger.info("=" * 50)
    logger.info("Monitoring Simulation Complete!")
    logger.info("=" * 50)
    logger.info(f"  Total days: {results['total_days']}")
    logger.info(f"  Processed: {results['processed_days']}")
    logger.info(f"  Failed: {results['failed_days']}")
    logger.info("")
    logger.info("View metrics in Grafana: http://localhost:3000")
    logger.info("View database in Adminer: http://localhost:8081")
    logger.info("=" * 50)

    results["status"] = "success"
    return results


if __name__ == "__main__":
    run_monitoring()
