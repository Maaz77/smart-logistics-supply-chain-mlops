"""
Streamlit UI for Logistics Delay Prediction.

Simple web interface to interact with the prediction API.
"""

import os

import requests
import streamlit as st

# Configuration
API_URL = os.getenv("API_URL", "http://serving-api:8000")
PREDICT_ENDPOINT = f"{API_URL}/predict"


def send_prediction_request(api_url: str, payload: dict) -> dict:
    """Send prediction request to the API.

    This is a pure Python function extracted from the Streamlit UI logic
    to make it testable without requiring Streamlit to be running.

    Args:
        api_url: The full URL to the prediction endpoint.
        payload: The request payload dictionary with 'data' key.

    Returns:
        Dictionary with prediction results or error information.
        On success: {"prediction": int, "probability": float}
        On error: {"error": str}
    """
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Page configuration
st.set_page_config(
    page_title="Logistics Delay Prediction",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 Logistics Delay Prediction")
st.markdown("Enter shipment details to predict logistics delay")

# Create form
with st.form("prediction_form"):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Location & Asset")
        latitude = st.number_input("Latitude", value=22.2748, format="%.4f")
        longitude = st.number_input("Longitude", value=-131.7086, format="%.4f")
        asset_id = st.text_input("Asset ID", value="Truck_6")
        inventory_level = st.number_input("Inventory Level", value=491, min_value=0)

    with col2:
        st.subheader("Shipment Details")
        shipment_status = st.selectbox(
            "Shipment Status",
            ["In Transit", "Delayed", "Delivered"],  # Only values from training data
            index=0,  # Default to "In Transit"
        )
        traffic_status = st.selectbox(
            "Traffic Status",
            ["Clear", "Detour", "Heavy"],  # Only values from training data
            index=0,  # Default to "Clear"
        )
        waiting_time = st.number_input("Waiting Time (minutes)", value=16, min_value=0)
        logistics_delay_reason = st.selectbox(
            "Logistics Delay Reason",
            ["None", "Weather", "Traffic", "Mechanical Failure"],  # Only values from training data
            index=0,  # Default to "None"
        )

    st.subheader("Environmental Conditions")
    col3, col4 = st.columns(2)
    with col3:
        temperature = st.number_input("Temperature (°C)", value=22.5, format="%.1f")
        humidity = st.number_input("Humidity (%)", value=54.3, format="%.1f")

    with col4:
        asset_utilization = st.number_input(
            "Asset Utilization (%)", value=80.9, format="%.1f", min_value=0.0, max_value=100.0
        )
        demand_forecast = st.number_input("Demand Forecast", value=174, min_value=0)

    st.subheader("User Information")
    col5, col6 = st.columns(2)
    with col5:
        user_transaction_amount = st.number_input(
            "User Transaction Amount", value=439.0, format="%.2f", min_value=0.0
        )
    with col6:
        user_purchase_frequency = st.number_input(
            "User Purchase Frequency", value=7, min_value=0
        )

    st.subheader("Timestamp")
    timestamp = st.text_input(
        "Timestamp (YYYY-MM-DD HH:MM:SS)",
        value="2024-10-30 07:53:51",
    )

    submitted = st.form_submit_button("Predict", use_container_width=True)

    if submitted:
        # Prepare request data with raw features
        # The API will handle preprocessing (temporal extraction, etc.)
        # For categorical features, we'll send the string values and let the API handle encoding
        # Note: The API will extract temporal features from Timestamp
        request_data = {
            "Timestamp": timestamp,
            "Latitude": latitude,
            "Longitude": longitude,
            "Inventory_Level": inventory_level,
            "Temperature": temperature,
            "Humidity": humidity,
            "Waiting_Time": waiting_time,
            "User_Transaction_Amount": user_transaction_amount,
            "User_Purchase_Frequency": user_purchase_frequency,
            "Asset_Utilization": asset_utilization,
            "Demand_Forecast": demand_forecast,
            # Categorical features (will be encoded by API if needed)
            "Shipment_Status": shipment_status,
            "Traffic_Status": traffic_status,
            "Logistics_Delay_Reason": logistics_delay_reason,
        }

        # Make prediction request using extracted function
        with st.spinner("Making prediction..."):
            result = send_prediction_request(PREDICT_ENDPOINT, {"data": request_data})

        # Check if there was an error
        if "error" in result:
            st.error(f"Error making prediction: {result['error']}")
        else:
            # Display results
            st.success("Prediction completed!")
            col7, col8 = st.columns(2)
            with col7:
                st.metric(
                    "Prediction",
                    "Delay" if result["prediction"] == 1 else "No Delay",
                )
            with col8:
                st.metric(
                    "Probability",
                    f"{result['probability']:.2%}",
                )

            # Show probability bar
            st.progress(result["probability"])

# Sidebar information
with st.sidebar:
    st.header("About")
    st.info(
        """
        This interface allows you to predict logistics delays
        based on shipment and environmental conditions.

        The model uses MLflow and is served via FastAPI.
        """
    )
    st.header("API Status")
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=5)
        if health_response.status_code == 200:
            st.success("✅ API is healthy")
            health_data = health_response.json()
            if health_data.get("model_loaded"):
                st.success("✅ Model is loaded")
            else:
                st.warning("⚠️ Model not loaded")
        else:
            st.error("❌ API is not responding")
    except Exception as e:
        st.error(f"❌ Cannot connect to API: {str(e)}")

    # Model Metadata Section
    st.header("📊 Model Information")
    try:
        metadata_response = requests.get(f"{API_URL}/model/metadata", timeout=5)
        if metadata_response.status_code == 200:
            metadata = metadata_response.json()

            # Model Details
            st.subheader("Model Details")
            st.text(f"Name: {metadata.get('model_name', 'N/A')}")
            st.text(f"Version: {metadata.get('model_version', 'N/A')}")
            if metadata.get("run_id"):
                # Display full Run ID using markdown code block to ensure it's not truncated
                st.markdown(f"**Run ID:**")
                st.markdown(f"```\n{metadata['run_id']}\n```")

            # Training Parameters
            st.subheader("Training Parameters")
            params = metadata.get("parameters", {})
            if params:
                # Display key parameters
                param_display = {
                    "best_estimator": params.get("best_estimator", "N/A"),
                    "n_iter": params.get("n_iter", "N/A"),
                    "metric": params.get("metric", "N/A"),
                    "train_size": params.get("train_size", "N/A"),
                    "val_size": params.get("val_size", "N/A"),
                    "test_size": params.get("test_size", "N/A"),
                    "n_features": params.get("n_features", "N/A"),
                }
                # Add hyperparameters (best_*)
                for key, value in params.items():
                    if key.startswith("best_") and key != "best_estimator":
                        param_display[key] = value

                for key, value in param_display.items():
                    st.text(f"{key}: {value}")

            # Performance Metrics
            st.subheader("Performance Metrics")
            metrics = metadata.get("metrics", {})
            if metrics:
                # Validation metrics
                if "val_roc_auc" in metrics:
                    st.metric("Validation ROC-AUC", f"{metrics['val_roc_auc']:.4f}")
                if "val_f1" in metrics:
                    st.metric("Validation F1 Score", f"{metrics['val_f1']:.4f}")

                # Test metrics
                if "test_roc_auc" in metrics:
                    st.metric("Test ROC-AUC", f"{metrics['test_roc_auc']:.4f}")
                if "test_f1" in metrics:
                    st.metric("Test F1 Score", f"{metrics['test_f1']:.4f}")
        else:
            st.warning("⚠️ Could not fetch model metadata")
    except Exception as e:
        st.warning(f"⚠️ Error loading model info: {str(e)}")
