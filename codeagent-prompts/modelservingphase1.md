***CODING_AGENT_PROMPT***
You are a Senior Backend Engineer. Implement the **Model Serving Microservices**.

**Context:**
- **Goal:** Create a Prediction API and a User Interface.
- **Architecture:** The API must resolve the model URI via MLflow, then download the artifacts directly from S3 (LocalStack).

**Requirements:**

1. **FastAPI Service (`src/serving/api.py`):**
   - **Endpoint:** `POST /predict`
   - **Startup Logic:**
     - Initialize MLflow Client.
     - Load model using: `mlflow.pyfunc.load_model("models:/LogisticsDelayModel@production")`.
     - **Error Handling:** If the alias doesn't exist, log a specific error: "Production model alias not found in MLflow."
   - **Prediction Logic:**
     - Receive JSON -> Convert to DataFrame.
     - Predict -> Return JSON `{"prediction": <int>, "probability": <float>}`.
     - **Logging:** Insert request/response into Postgres table `serving_logs`.

2. **Dockerization (`./serving/docker/Dockerfile.serving` & `./serving/docker-compose.serving.yaml`):**
   - **FastAPI Container:**
     - Expose Port 8000.
     - **Crucial Environment Variables (for S3 Access):**
       - `MLFLOW_TRACKING_URI=http://mlflow-server:5000`
       - `MLFLOW_S3_ENDPOINT_URL=http://localstack:4566`
       - `AWS_ACCESS_KEY_ID=test` (Standard LocalStack creds)
       - `AWS_SECRET_ACCESS_KEY=test`
       - `AWS_DEFAULT_REGION=us-east-1`
     - **Network:** Must share the same network as `mlflow-server` and `localstack`.

3. **Streamlit UI (`src/serving/ui.py`):**
   - Simple form to input features.
   - POSTs to `http://serving-api:8000/predict`.

**Definition of Done:**
- `make serving` starts containers.
- The FastAPI logs show: "Successfully loaded model from s3://..." (Proving both MLflow and S3 connections worked).
- The UI gets a valid prediction.
