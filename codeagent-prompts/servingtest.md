You are a Senior QA/MLOps Engineer. Implement a complete **Integration Test Suite** for the Model Serving system (API + UI) and add it to CI.

**Context:**
- **Component A:** FastAPI service (`src/serving/api.py`). Connects to MLflow/S3/Postgres.
- **Component B:** Streamlit UI (`src/serving/ui.py`). Connects to Component A.
- **Goal:** Verify the code logic and the JSON contract between A and B without running Docker/LocalStack.

**Requirements:**

1. **Dependency Management:**
   - Add `pytest`, `httpx` (for API testing), and `pytest-mock` to `pyproject.toml`.

2. **Refactor UI Logic (`src/serving/ui.py`):**
   - Extract the API request logic from the Streamlit rendering code into a pure Python function.
   - **Create Function:**
     ```python
     def send_prediction_request(api_url: str, payload: dict) -> dict:
         try:
             response = requests.post(api_url, json=payload, timeout=5)
             response.raise_for_status()
             return response.json()
         except requests.exceptions.RequestException as e:
             return {"error": str(e)}
     ```
   - Update the Streamlit button code to call this function instead of calling `requests.post` directly.

3. **Server-Side Tests (`tests/test_api.py`):**
   - Use `fastapi.testclient.TestClient`.
   - **Mocking (Critical):**
     - Patch `src.serving.api.mlflow.pyfunc.load_model`. Configure the mock to return an object with a `.predict()` method that returns `[0]` or `[1]`.
     - Patch `src.serving.api.psycopg.connect`. Return a mock connection/cursor to prevent DB errors during logging.
   - **Test Cases:**
     - `test_prediction_endpoint_success`: Send valid JSON. Assert status 200 and response schema.
     - `test_prediction_endpoint_validation_error`: Send empty JSON. Assert status 422.

4. **Client-Side Tests (`tests/test_ui.py`):**
   - Import `send_prediction_request` from `src.serving.ui`.
   - **Mocking:**
     - Patch `requests.post`.
   - **Test Cases:**
     - `test_ui_sends_correct_payload`: Call `send_prediction_request` with sample data. Assert `requests.post` was called with the correct URL and the EXACT JSON payload expected by the API.
     - `test_ui_handles_connection_error`: Configure mock to raise `ConnectionError`. Assert function returns the error dict.

5. **CI Pipeline (`.github/workflows/ci.yaml`):**
   - Add a step to `Run Tests`:
     ```yaml
     - name: Run Integration Tests
       run: |
         pip install pytest httpx pytest-mock requests
         export PYTHONPATH=$PYTHONPATH:.
         pytest tests/ -v
     ```

**Constraints:**
- Tests must NOT require AWS credentials, S3, or Postgres to be running.
- Use `unittest.mock` or `pytest-mocker` fixture.

**Definition of Done:**
- Running `pytest` locally passes 100%.
- The UI logic is decoupled from Streamlit widgets (making it testable).
- CI pipeline includes the test step.
