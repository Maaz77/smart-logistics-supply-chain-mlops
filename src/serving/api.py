"""
FastAPI Model Serving Service for Smart Logistics Supply Chain.

Provides a prediction API that loads models from MLflow and serves predictions.
"""

import io
import json
import logging
import os
from datetime import datetime
from typing import Any

import mlflow
import pandas as pd
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sklearn.preprocessing import LabelEncoder

from src.ml_pipeline.common import (
    get_data_bucket,
    get_postgres_connection_string,
    get_s3_client,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Logistics Delay Prediction API", version="1.0.0")

# Global model variable
model = None
model_uri = None
categorical_encoders: dict[str, LabelEncoder] = {}
expected_feature_order: list[str] = []

# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_ALIAS = os.getenv("MODEL_ALIAS")
CATEGORICAL_COLUMNS = ["Shipment_Status", "Traffic_Status", "Logistics_Delay_Reason"]
logger.info(f"Heeeey there, the model name is: {MODEL_NAME}")
logger.info(f"Heeeey there, the model alias is: {MODEL_ALIAS}")

class ModelMetadataResponse(BaseModel):
    """Response model for model metadata endpoint."""

    model_name: str
    model_version: str | None
    run_id: str | None
    parameters: dict[str, Any]
    metrics: dict[str, float]
    model_uri: str | None


class PredictionRequest(BaseModel):
    """Request model for prediction endpoint."""

    # Accept flexible input - can be a single record or list of records
    data: list[dict[str, Any]] | dict[str, Any]


class PredictionResponse(BaseModel):
    """Response model for prediction endpoint."""

    prediction: int | list[int]
    probability: float | list[float]


def init_db_table() -> None:
    """Initialize the serving_logs table in Postgres if it doesn't exist."""
    try:
        conn_str = get_postgres_connection_string()
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()

        # Create serving_logs table if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS serving_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                request_data JSONB,
                prediction INTEGER,
                probability FLOAT,
                model_uri TEXT,
                error_message TEXT
            )
            """
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✓ serving_logs table initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize serving_logs table: {e}")


def log_to_db(
    request_data: dict | list,
    prediction: int | list[int] | None = None,
    probability: float | list[float] | None = None,
    error_message: str | None = None,
) -> None:
    """Log request and response to Postgres serving_logs table."""
    try:
        conn_str = get_postgres_connection_string()
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO serving_logs (request_data, prediction, probability, model_uri, error_message)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                json.dumps(request_data),
                prediction,
                probability,
                model_uri,
                error_message,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")


def load_model() -> None:
    """Load model from MLflow using the configured alias."""
    global model, model_uri

    try:
        # Configure MLflow tracking URI
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        logger.info(f"MLflow tracking URI: {tracking_uri}")
        mlflow.set_tracking_uri(tracking_uri)

        # Configure S3 endpoint for artifact access
        os.environ["MLFLOW_S3_ENDPOINT_URL"] = os.getenv(
            "MLFLOW_S3_ENDPOINT_URL", "http://localstack:4566"
        )
        os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "test")
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        # Get model name and alias from environment (allows switching models via ConfigMap)
        model_name = os.getenv("MODEL_NAME", MODEL_NAME)
        model_alias = os.getenv("MODEL_ALIAS", MODEL_ALIAS)
        logger.info(f"Using model name: {model_name}, alias: {model_alias}")

        # Load model using MLflow model registry alias
        model_uri = f"models:/{model_name}@{model_alias}"
        logger.info(f"Loading model from: {model_uri}")

        model = mlflow.pyfunc.load_model(model_uri)

        # Log success with model URI from MLflow
        if hasattr(model, "metadata") and hasattr(model.metadata, "model_uri"):
            actual_uri = model.metadata.model_uri
            logger.info(f"✓ Successfully loaded model from {actual_uri}")
            if "s3://" in str(actual_uri):
                logger.info(f"✓ Model artifacts loaded from S3: {actual_uri}")
        else:
            logger.info(f"✓ Successfully loaded model from {model_uri}")

    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "not found" in error_msg.lower():
            logger.error("Production model alias not found in MLflow.")
            raise RuntimeError(
                "Production model alias not found in MLflow. Please ensure a model is registered with the 'production' alias."
            )
        else:
            logger.error(f"Failed to load model: {error_msg}")
            raise RuntimeError(f"Failed to load model: {error_msg}")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize model and database on startup."""
    logger.info("=" * 50)
    logger.info("Starting Logistics Delay Prediction API")
    logger.info("=" * 50)

    # Initialize database table
    init_db_table()

    # Load feature order and categorical encoders
    global categorical_encoders, expected_feature_order
    expected_feature_order, categorical_encoders = load_feature_order_and_encoders()

    # Load model
    load_model()

    logger.info("=" * 50)
    logger.info("API ready to serve predictions")
    logger.info("=" * 50)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": "true" if model is not None else "false",
    }


@app.get("/model/metadata", response_model=ModelMetadataResponse)
async def get_model_metadata() -> ModelMetadataResponse:
    """Get model metadata from MLflow including parameters and metrics.

    Returns:
        Model metadata with parameters and performance metrics.
    """
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please check server logs for details.",
        )

    try:
        logger.info("Fetching model metadata from MLflow...")
        # Get MLflow client
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow_client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
        logger.info(f"MLflow client created, tracking URI: {tracking_uri}")

        # Get run_id from the loaded model's metadata
        if not hasattr(model, 'metadata'):
            logger.error("Model does not have metadata attribute")
            raise HTTPException(
                status_code=500,
                detail="Loaded model does not have metadata attribute.",
            )

        if not hasattr(model.metadata, 'run_id'):
            logger.error("Model metadata does not have run_id")
            raise HTTPException(
                status_code=500,
                detail="Loaded model does not have run_id in metadata.",
            )

        run_id = model.metadata.run_id
        logger.info(f"Got run_id from model: {run_id}")

        # Get run details from MLflow
        try:
            run = mlflow_client.get_run(run_id)
            logger.info(f"Retrieved run from MLflow: {run_id}")
        except Exception as e:
            logger.error(f"Failed to get run from MLflow: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve run from MLflow: {str(e)}",
            )

        # Try to find the model version that corresponds to this run
        try:
            model_name = os.getenv("MODEL_NAME", MODEL_NAME)
            model_versions = mlflow_client.search_model_versions(
                filter_string=f"name='{model_name}'"
            )
            logger.info(f"Found {len(model_versions)} model versions")
        except Exception as e:
            logger.warning(f"Could not search model versions: {e}, continuing without version info")
            model_versions = []

        version = None
        model_source_uri = model_uri if model_uri else None
        for mv in model_versions:
            if mv.run_id == run_id:
                version = mv.version
                model_source_uri = mv.source
                logger.info(f"Found matching version: {version}")
                break

        # Extract parameters and metrics
        parameters = dict(run.data.params) if run.data.params else {}
        metrics = {k: float(v) for k, v in run.data.metrics.items()} if run.data.metrics else {}
        logger.info(f"Extracted {len(parameters)} parameters and {len(metrics)} metrics")

        model_name = os.getenv("MODEL_NAME", MODEL_NAME)
        return ModelMetadataResponse(
            model_name=model_name,
            model_version=version,
            run_id=run_id,
            parameters=parameters,
            metrics=metrics,
            model_uri=model_source_uri,
        )

    except HTTPException as he:
        # Re-raise HTTPExceptions as-is
        raise he
    except Exception as e:
        # Extract error message
        error_msg = str(e) if e else "Unknown error"
        if not error_msg or error_msg.strip() == "":
            error_msg = f"{type(e).__name__}: {repr(e)}"
        logger.error(f"Error fetching model metadata: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch model metadata: {error_msg}",
        )


@app.get("/predict")
async def predict_get() -> dict[str, str]:
    """GET handler for /predict endpoint (returns usage info)."""
    return {
        "error": "Method Not Allowed",
        "message": "Please use POST method to make predictions",
        "example": "POST /predict with JSON body containing 'data' field with feature values",
    }


def load_feature_order_and_encoders() -> tuple[list[str], dict[str, LabelEncoder]]:
    """Load feature order and categorical encoders from training data.

    Returns:
        Tuple of (expected feature order list, encoders dict).
    """
    feature_order = []
    encoders = {}
    try:
        # Override S3 endpoint for container-to-container communication
        import boto3
        endpoint_url = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://localstack:4566")
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )
        bucket = get_data_bucket()

        # Load processed training data to get feature order
        processed_key = "processed/train.parquet"
        logger.info(f"Loading feature order from s3://{bucket}/{processed_key}")
        response = s3_client.get_object(Bucket=bucket, Key=processed_key)
        processed_df = pd.read_parquet(io.BytesIO(response["Body"].read()))

        # Get feature columns (drop Timestamp and target)
        cols_to_drop = ["Timestamp", "Logistics_Delay", "Asset_ID"]
        feature_order = [
            col for col in processed_df.columns
            if col not in cols_to_drop
        ]
        # Keep only numeric columns (as model expects)
        numeric_cols = processed_df[feature_order].select_dtypes(
            include=["int64", "float64", "int32", "float32"]
        ).columns.tolist()
        feature_order = numeric_cols
        logger.info(f"Feature order: {feature_order}")

        # Load raw data to get encoders
        raw_key = "raw/logistics.csv"
        logger.info(f"Loading encoders from s3://{bucket}/{raw_key}")
        response = s3_client.get_object(Bucket=bucket, Key=raw_key)
        raw_df = pd.read_csv(io.BytesIO(response["Body"].read()))

        # Create encoders based on raw training data (before encoding)
        for col in CATEGORICAL_COLUMNS:
            if col in raw_df.columns:
                encoder = LabelEncoder()
                # Get unique values from raw data (these are strings)
                unique_vals = raw_df[col].fillna("None").astype(str).unique()
                encoder.fit(unique_vals)
                encoders[col] = encoder
                logger.info(f"Loaded encoder for {col}: {len(unique_vals)} unique values - {sorted(list(unique_vals))}")
            else:
                logger.warning(f"Column {col} not found in raw data")

    except Exception as e:
        logger.error(f"Failed to load feature order and encoders: {e}", exc_info=True)
        logger.warning("Feature ordering and categorical encoding may not work correctly")

    return feature_order, encoders




def prepare_features_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare features for prediction by ensuring they match training format.

    Args:
        df: Input DataFrame with features.

    Returns:
        DataFrame with prepared features (numeric only, matching training format).
    """
    df = df.copy()

    # Drop non-feature columns if present
    cols_to_drop = ["Logistics_Delay", "Asset_ID"]
    for col in cols_to_drop:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Extract temporal features from Timestamp if present
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["hour"] = df["Timestamp"].dt.hour
        df["day_of_week"] = df["Timestamp"].dt.dayofweek
        df["month"] = df["Timestamp"].dt.month
        df = df.drop(columns=["Timestamp"])

    # Encode categorical columns if encoders are available
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            if col in categorical_encoders:
                encoder = categorical_encoders[col]
                # Fill NaN and handle "None" string
                df[col] = df[col].fillna("None").astype(str)
                # Replace "None" string with actual None for encoding
                df[col] = df[col].replace("None", "None")  # Keep as string
                # Handle unknown values
                try:
                    df[col] = encoder.transform(df[col])
                    logger.debug(f"Encoded {col} successfully")
                except ValueError as e:
                    # If value not seen in training, try to find closest match
                    logger.warning(f"Unknown value in {col}: {e}, attempting fallback")
                    # Try to map common variations
                    unique_vals = df[col].unique()
                    for val in unique_vals:
                        if val not in encoder.classes_:
                            # Try to find a similar value
                            if "None" in encoder.classes_:
                                df[col] = df[col].replace(val, "None")
                            else:
                                df[col] = df[col].replace(val, encoder.classes_[0])
                    try:
                        df[col] = encoder.transform(df[col])
                    except ValueError:
                        logger.error(f"Failed to encode {col}, using default value 0")
                        df[col] = 0
            else:
                logger.warning(f"Encoder not found for {col}, column will be dropped")

    # Keep only numeric columns (matching training format)
    numeric_cols = df.select_dtypes(
        include=["int64", "float64", "int32", "float32"]
    ).columns
    df = df[numeric_cols]

    # Reorder columns to match training order
    if expected_feature_order:
        # Get columns that exist in both
        available_cols = [col for col in expected_feature_order if col in df.columns]
        # Add any missing columns (shouldn't happen, but handle gracefully)
        missing_cols = [col for col in expected_feature_order if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing columns in prediction data: {missing_cols}")
            # Fill with zeros for missing columns
            for col in missing_cols:
                df[col] = 0
        # Reorder to match training order
        df = df[expected_feature_order]
        logger.debug(f"Reordered features to match training order: {list(df.columns)}")
    else:
        logger.warning("Expected feature order not loaded, using current column order")

    return df


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest) -> PredictionResponse:
    """Predict logistics delay for given features.

    Args:
        request: Prediction request with feature data.

    Returns:
        Prediction response with prediction and probability.
    """
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please check server logs for details.",
        )

    try:
        # Convert request to DataFrame
        if isinstance(request.data, dict):
            # Single record
            df = pd.DataFrame([request.data])
        else:
            # Multiple records
            df = pd.DataFrame(request.data)

        # Prepare features (ensure they match training format)
        df = prepare_features_for_prediction(df)

        # Log feature columns for debugging
        logger.info(f"Features after preprocessing: {list(df.columns)}")
        logger.info(f"Feature shape: {df.shape}")

        # Make prediction
        predictions = model.predict(df)

        # Get probabilities from the underlying sklearn model
        # MLflow pyfunc models wrap sklearn models, _model_impl has predict_proba method
        try:
            if hasattr(model, "_model_impl") and hasattr(model._model_impl, "predict_proba"):
                probabilities = model._model_impl.predict_proba(df)[:, 1]  # Probability of class 1
            else:
                # Fallback: access sklearn_model directly
                if hasattr(model, "_model_impl") and hasattr(model._model_impl, "sklearn_model"):
                    sklearn_model = model._model_impl.sklearn_model
                    probabilities = sklearn_model.predict_proba(df)[:, 1]
                else:
                    logger.warning("Cannot access predict_proba, using prediction as probability")
                    probabilities = predictions.astype(float)
        except Exception as e:
            logger.warning(f"Error getting probabilities: {e}, using prediction as probability")
            probabilities = predictions.astype(float)

        # Convert to appropriate format
        if len(predictions) == 1:
            prediction = int(predictions[0])
            probability = float(probabilities[0])
        else:
            prediction = [int(p) for p in predictions]
            probability = [float(p) for p in probabilities]

        # Log to database
        log_to_db(
            request_data=request.data,
            prediction=prediction,
            probability=probability,
        )

        return PredictionResponse(prediction=prediction, probability=probability)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Prediction error: {error_msg}")

        # Log error to database
        log_to_db(
            request_data=request.data,
            error_message=error_msg,
        )

        raise HTTPException(status_code=400, detail=f"Prediction failed: {error_msg}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
