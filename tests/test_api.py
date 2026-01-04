"""
Integration tests for the FastAPI serving API.

Tests the prediction endpoint with mocked MLflow model and database connections.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.serving.api import app


@pytest.fixture
def mock_model():
    """Create a mock MLflow model with predict and predict_proba methods."""
    mock = MagicMock()
    mock.predict.return_value = np.array([0])
    mock.predict_proba.return_value = np.array([[0.8, 0.2]])  # [prob_class_0, prob_class_1]
    mock.metadata = MagicMock()
    mock.metadata.run_id = "test_run_id_12345"
    mock.metadata.model_uri = "s3://test-bucket/model"
    mock._model_impl = MagicMock()
    mock._model_impl.predict_proba.return_value = np.array([[0.8, 0.2]])
    return mock


@pytest.fixture
def mock_encoders():
    """Create mock categorical encoders."""
    from sklearn.preprocessing import LabelEncoder

    encoders = {}
    for col in ["Shipment_Status", "Traffic_Status", "Logistics_Delay_Reason"]:
        encoder = LabelEncoder()
        encoder.fit(["In Transit", "Delayed", "Delivered"] if col == "Shipment_Status" else ["Clear", "Detour", "Heavy"] if col == "Traffic_Status" else ["None", "Weather", "Traffic", "Mechanical Failure"])
        encoders[col] = encoder
    return encoders


@pytest.fixture
def mock_feature_order():
    """Return expected feature order."""
    return [
        "Latitude",
        "Longitude",
        "Inventory_Level",
        "Shipment_Status",
        "Temperature",
        "Humidity",
        "Traffic_Status",
        "Waiting_Time",
        "User_Transaction_Amount",
        "User_Purchase_Frequency",
        "Logistics_Delay_Reason",
        "Asset_Utilization",
        "Demand_Forecast",
        "hour",
        "day_of_week",
        "month",
    ]


@pytest.fixture
def client(mock_model, mock_encoders, mock_feature_order):
    """Create a test client with mocked dependencies."""
    # Import the module to access its globals
    import src.serving.api as api_module

    # Set the global variables directly
    api_module.model = mock_model
    api_module.categorical_encoders = mock_encoders
    api_module.expected_feature_order = mock_feature_order
    api_module.model_uri = "models:/LogisticsDelayModel@production"

    # Patch functions that would try to connect to external services
    with patch("src.serving.api.load_model"), \
         patch("src.serving.api.load_feature_order_and_encoders", return_value=(mock_feature_order, mock_encoders)), \
         patch("src.serving.api.init_db_table"), \
         patch("src.serving.api.log_to_db"), \
         patch("src.serving.api.get_postgres_connection_string", return_value="postgresql://test:test@localhost:5432/test"), \
         patch("psycopg2.connect") as mock_connect:
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.commit = MagicMock()
        mock_connect.return_value = mock_conn
        yield TestClient(app)


def test_prediction_endpoint_success(client, mock_model):
    """Test successful prediction request."""
    # Prepare valid request payload
    payload = {
        "data": {
            "Timestamp": "2024-10-30 07:53:51",
            "Latitude": 22.2748,
            "Longitude": -131.7086,
            "Inventory_Level": 491,
            "Temperature": 22.5,
            "Humidity": 54.3,
            "Waiting_Time": 16,
            "User_Transaction_Amount": 439.0,
            "User_Purchase_Frequency": 7,
            "Asset_Utilization": 80.9,
            "Demand_Forecast": 174,
            "Shipment_Status": "In Transit",
            "Traffic_Status": "Clear",
            "Logistics_Delay_Reason": "None",
        }
    }

    # Make request
    response = client.post("/predict", json=payload)

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    assert isinstance(data["prediction"], int)
    assert isinstance(data["probability"], (int, float))
    assert 0 <= data["probability"] <= 1

    # Verify model was called
    assert mock_model.predict.called or mock_model._model_impl.predict_proba.called


def test_prediction_endpoint_validation_error(client):
    """Test prediction endpoint with invalid/empty payload."""
    # Test with missing data field (should trigger Pydantic validation)
    payload = {}
    response = client.post("/predict", json=payload)
    assert response.status_code == 422  # Validation error
    assert "detail" in response.json()

    # Test with invalid JSON structure
    payload = {"data": "not a dict or list"}
    response = client.post("/predict", json=payload)
    # This might pass validation but fail later, or fail validation depending on Pydantic config
    # Let's test with completely invalid JSON
    response = client.post("/predict", data="invalid json", headers={"Content-Type": "application/json"})
    assert response.status_code in [400, 422]  # Either bad request or validation error


def test_prediction_endpoint_model_not_loaded(client):
    """Test prediction endpoint when model is not loaded."""
    with patch("src.serving.api.model", None):
        payload = {
            "data": {
                "Timestamp": "2024-10-30 07:53:51",
                "Latitude": 22.2748,
                "Longitude": -131.7086,
                "Inventory_Level": 491,
                "Temperature": 22.5,
                "Humidity": 54.3,
                "Waiting_Time": 16,
                "User_Transaction_Amount": 439.0,
                "User_Purchase_Frequency": 7,
                "Asset_Utilization": 80.9,
                "Demand_Forecast": 174,
                "Shipment_Status": "In Transit",
                "Traffic_Status": "Clear",
                "Logistics_Delay_Reason": "None",
            }
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 503
        assert "not loaded" in response.json()["detail"].lower()


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data


def test_predict_get_endpoint(client):
    """Test GET /predict endpoint returns usage info."""
    response = client.get("/predict")
    assert response.status_code == 200
    data = response.json()
    assert "error" in data or "message" in data
    assert "POST" in str(data.get("message", data.get("error", ""))).upper()
