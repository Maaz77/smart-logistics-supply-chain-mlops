"""
Integration tests for the Streamlit UI client logic.

Tests the send_prediction_request function with mocked requests.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

# Mock streamlit before importing ui module to prevent execution of Streamlit code
import sys
from unittest.mock import MagicMock as Mock

# Create comprehensive streamlit mock
mock_st = Mock()
mock_st.columns.return_value = [Mock(), Mock()]
mock_st.number_input.return_value = 0.0
mock_st.text_input.return_value = ""
mock_st.selectbox.return_value = ""
mock_st.form.return_value.__enter__ = Mock(return_value=Mock())
mock_st.form.return_value.__exit__ = Mock(return_value=False)
mock_st.form_submit_button.return_value = False
mock_st.sidebar = Mock()
mock_st.subheader = Mock()
mock_st.header = Mock()
mock_st.text = Mock()
mock_st.markdown = Mock()
mock_st.metric = Mock()
mock_st.progress = Mock()
mock_st.success = Mock()
mock_st.error = Mock()
mock_st.warning = Mock()
mock_st.info = Mock()
mock_st.spinner.return_value.__enter__ = Mock(return_value=Mock())
mock_st.spinner.return_value.__exit__ = Mock(return_value=False)
mock_st.set_page_config = Mock()

sys.modules['streamlit'] = mock_st

# Now import the function we want to test
from src.serving.ui import send_prediction_request


def test_ui_sends_correct_payload():
    """Test that send_prediction_request sends the correct payload to the API."""
    api_url = "http://test-api:8000/predict"
    request_data = {
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
    expected_payload = {"data": request_data}

    # Mock the requests.post function
    with patch("src.serving.ui.requests.post") as mock_post:
        # Configure mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"prediction": 0, "probability": 0.12}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Call the function
        result = send_prediction_request(api_url, expected_payload)

        # Assertions
        assert result == {"prediction": 0, "probability": 0.12}

        # Verify requests.post was called with correct arguments
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == api_url  # URL
        assert call_args[1]["json"] == expected_payload  # JSON payload
        assert call_args[1]["timeout"] == 10  # Timeout


def test_ui_handles_connection_error():
    """Test that send_prediction_request handles connection errors gracefully."""
    api_url = "http://test-api:8000/predict"
    payload = {"data": {"test": "data"}}

    # Mock requests.post to raise ConnectionError
    with patch("src.serving.ui.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Call the function
        result = send_prediction_request(api_url, payload)

        # Assertions
        assert "error" in result
        assert "Connection" in result["error"] or "refused" in result["error"].lower()


def test_ui_handles_http_error():
    """Test that send_prediction_request handles HTTP errors gracefully."""
    api_url = "http://test-api:8000/predict"
    payload = {"data": {"test": "data"}}

    # Mock requests.post to raise HTTPError
    with patch("src.serving.ui.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        # Call the function
        result = send_prediction_request(api_url, payload)

        # Assertions
        assert "error" in result
        assert "400" in result["error"] or "Bad Request" in result["error"]


def test_ui_handles_timeout_error():
    """Test that send_prediction_request handles timeout errors gracefully."""
    api_url = "http://test-api:8000/predict"
    payload = {"data": {"test": "data"}}

    # Mock requests.post to raise Timeout
    with patch("src.serving.ui.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        # Call the function
        result = send_prediction_request(api_url, payload)

        # Assertions
        assert "error" in result
        assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()


def test_ui_handles_successful_response():
    """Test that send_prediction_request correctly processes successful responses."""
    api_url = "http://test-api:8000/predict"
    payload = {"data": {"test": "data"}}
    expected_response = {"prediction": 1, "probability": 0.85}

    # Mock successful response
    with patch("src.serving.ui.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Call the function
        result = send_prediction_request(api_url, payload)

        # Assertions
        assert result == expected_response
        assert result["prediction"] == 1
        assert result["probability"] == 0.85
