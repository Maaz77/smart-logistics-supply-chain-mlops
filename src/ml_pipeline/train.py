"""
Model Training Module for Smart Logistics Supply Chain.

Reads data from S3, trains model, and registers with MLflow.
MLflow artifacts are stored in S3 (mlflow-model-registry bucket).
"""

import io
import logging
import os

import mlflow
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV

from src.ml_pipeline.common import (
    get_data_bucket,
    get_mlflow_tracking_uri,
    get_s3_client,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
S3_PROCESSED_PREFIX = "processed"
MODEL_NAME = "Logistics-Delay-Model"
EXPERIMENT_NAME = "logistics-delay-prediction-experiments"
TARGET_COLUMN = "Logistics_Delay"

# Training settings
METRIC = "roc_auc"
N_ITER = 50  # Number of RandomizedSearchCV iterations


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
    return df


def load_processed_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load processed train/val/test splits from S3.

    Returns:
        Tuple of (train_df, val_df, test_df).
    """
    train_df = load_dataframe_from_s3(f"{S3_PROCESSED_PREFIX}/train.parquet")
    val_df = load_dataframe_from_s3(f"{S3_PROCESSED_PREFIX}/val.parquet")
    test_df = load_dataframe_from_s3(f"{S3_PROCESSED_PREFIX}/test.parquet")

    logger.info(
        f"Loaded - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}"
    )
    return train_df, val_df, test_df


def prepare_features(
    df: pd.DataFrame, drop_cols: list[str] | None = None
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare features and target from DataFrame.

    Args:
        df: Input DataFrame.
        drop_cols: Columns to drop (non-feature columns).

    Returns:
        Tuple of (features DataFrame, target Series).
    """
    if drop_cols is None:
        # Default columns to drop (non-features)
        drop_cols = ["Timestamp", TARGET_COLUMN]

    # Get available columns to drop
    cols_to_drop = [col for col in drop_cols if col in df.columns]

    X = df.drop(columns=cols_to_drop, errors="ignore")
    y = df[TARGET_COLUMN] if TARGET_COLUMN in df.columns else None

    # Drop any remaining non-numeric columns
    numeric_cols = X.select_dtypes(
        include=["int64", "float64", "int32", "float32"]
    ).columns
    X = X[numeric_cols]

    return X, y


def train_model_sklearn(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> tuple[object, str, dict]:
    """Train model using sklearn model selection.

    Tries multiple estimators and selects the best one based on ROC-AUC.

    Args:
        X_train: Training features.
        y_train: Training target.
        X_val: Validation features.
        y_val: Validation target.

    Returns:
        Tuple of (best_model, best_estimator_name, best_config).
    """
    logger.info("Starting sklearn-based model selection")

    # Combine train and val for cross-validation
    X_combined = pd.concat([X_train, X_val], ignore_index=True)
    y_combined = pd.concat([y_train, y_val], ignore_index=True)

    # Define candidate models with hyperparameter grids
    candidates = {
        "RandomForest": {
            "estimator": RandomForestClassifier(random_state=42, n_jobs=-1),
            "params": {
                "n_estimators": [50, 100, 200],
                "max_depth": [5, 10, 20, None],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
            },
        },
        "GradientBoosting": {
            "estimator": GradientBoostingClassifier(random_state=42),
            "params": {
                "n_estimators": [50, 100, 200],
                "max_depth": [3, 5, 7],
                "learning_rate": [0.01, 0.1, 0.2],
                "min_samples_split": [2, 5, 10],
            },
        },
        "LogisticRegression": {
            "estimator": LogisticRegression(random_state=42, max_iter=1000),
            "params": {
                "C": [0.01, 0.1, 1, 10],
                "l1_ratio": [0.0, 0.5, 1.0],
                "solver": ["saga"],
                "penalty": ["elasticnet"],
            },
        },
    }

    best_model = None
    best_score = 0
    best_name = ""
    best_config = {}

    for name, config in candidates.items():
        logger.info(f"Tuning {name}...")

        search = RandomizedSearchCV(
            estimator=config["estimator"],
            param_distributions=config["params"],
            n_iter=min(N_ITER, 20),
            scoring="roc_auc",
            cv=3,
            random_state=42,
            n_jobs=-1,
        )

        search.fit(X_combined, y_combined)

        logger.info(f"  {name} best score: {search.best_score_:.4f}")

        if search.best_score_ > best_score:
            best_score = search.best_score_
            best_model = search.best_estimator_
            best_name = name
            best_config = search.best_params_

    logger.info(f"Best estimator: {best_name} with score {best_score:.4f}")
    logger.info(f"Best config: {best_config}")

    return best_model, best_name, best_config


def evaluate_model(
    model: object,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict:
    """Evaluate model on validation and test sets.

    Args:
        model: Trained model instance.
        X_val: Validation features.
        y_val: Validation target.
        X_test: Test features.
        y_test: Test target.

    Returns:
        Dictionary with evaluation metrics.
    """
    metrics = {}

    # Validation metrics
    val_pred = model.predict(X_val)
    val_pred_proba = model.predict_proba(X_val)[:, 1]
    metrics["val_roc_auc"] = roc_auc_score(y_val, val_pred_proba)
    metrics["val_f1"] = f1_score(y_val, val_pred)

    # Test metrics
    test_pred = model.predict(X_test)
    test_pred_proba = model.predict_proba(X_test)[:, 1]
    metrics["test_roc_auc"] = roc_auc_score(y_test, test_pred_proba)
    metrics["test_f1"] = f1_score(y_test, test_pred)

    logger.info(f"Validation ROC-AUC: {metrics['val_roc_auc']:.4f}")
    logger.info(f"Validation F1: {metrics['val_f1']:.4f}")
    logger.info(f"Test ROC-AUC: {metrics['test_roc_auc']:.4f}")
    logger.info(f"Test F1: {metrics['test_f1']:.4f}")

    return metrics


def run_training() -> dict:
    """Run the full training pipeline with MLflow tracking.

    Reads data from S3, trains model, and stores artifacts in S3.

    Returns:
        Dictionary with training results.
    """
    logger.info("=" * 50)
    logger.info("Starting Model Training Pipeline")
    logger.info("=" * 50)

    # Configure MLflow
    tracking_uri = get_mlflow_tracking_uri()
    logger.info(f"MLflow tracking URI: {tracking_uri}")
    mlflow.set_tracking_uri(tracking_uri)

    # Set S3 endpoint for artifact storage (MLflow stores in mlflow-model-registry bucket)
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = os.getenv(
        "AWS_ENDPOINT_URL", "http://localhost:4566"
    )
    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "test")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

    # Create or get experiment
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Load data from S3
    train_df, val_df, test_df = load_processed_data()

    # Prepare features
    X_train, y_train = prepare_features(train_df)
    X_val, y_val = prepare_features(val_df)
    X_test, y_test = prepare_features(test_df)

    logger.info(f"Feature columns: {list(X_train.columns)}")

    # Start MLflow run
    with mlflow.start_run(run_name="sklearn_automl") as run:
        run_id = run.info.run_id
        logger.info(f"MLflow run ID: {run_id}")

        # Log parameters
        mlflow.log_param("n_iter", N_ITER)
        mlflow.log_param("metric", METRIC)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("val_size", len(X_val))
        mlflow.log_param("test_size", len(X_test))
        mlflow.log_param("n_features", len(X_train.columns))

        # Train model
        model, best_name, best_config = train_model_sklearn(
            X_train, y_train, X_val, y_val
        )

        # Log best estimator info
        mlflow.log_param("best_estimator", best_name)
        for k, v in best_config.items():
            mlflow.log_param(f"best_{k}", v)

        # Evaluate model
        metrics = evaluate_model(model, X_val, y_val, X_test, y_test)

        # Log metrics
        mlflow.log_metrics(metrics)

        # Log model (stored in S3 mlflow-model-registry bucket)
        logger.info(f"Logging model to MLflow as '{MODEL_NAME}'")
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )

        logger.info(f"Model registered as '{MODEL_NAME}'")

    result = {
        "run_id": run_id,
        "model_name": MODEL_NAME,
        "best_estimator": best_name,
        "metrics": metrics,
        "status": "success",
    }

    logger.info("=" * 50)
    logger.info("Model Training Complete!")
    logger.info(f"  Run ID: {run_id}")
    logger.info(f"  Model: {MODEL_NAME}")
    logger.info(f"  Best Estimator: {best_name}")
    logger.info(f"  Test ROC-AUC: {metrics['test_roc_auc']:.4f}")
    logger.info("=" * 50)

    return result


if __name__ == "__main__":
    run_training()
