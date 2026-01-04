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

        try:
            # Make prediction request
            with st.spinner("Making prediction..."):
                response = requests.post(
                    PREDICT_ENDPOINT,
                    json={"data": request_data},
                    timeout=10,
                )
                response.raise_for_status()
                result = response.json()

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

        except requests.exceptions.RequestException as e:
            st.error(f"Error making prediction: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    st.error(f"Details: {error_detail}")
                except Exception:
                    st.error(f"Response: {e.response.text}")

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
