You are a Senior MLOps Engineer. Phase 1 (Infrastructure) is complete. Your task is to implement **Phase 2: The Monitoring Simulation** using a **Sequential Task Chain** pattern.

**Context:**
- **Infrastructure:** `grafana` (Port 3000) and `adminer` (Port 8081) are running.
- **Database:** `mlflow-postgres` container has a `monitoring` database (Port 5432).
- **Data:** `val.parquet` on the s3 bucket contains validation data from `2024-09-14` to `2024-11-09`.
- **Goal:** A Manual Airflow DAG that processes this date range day-by-day. In the UI, we want to see a separate TaskGroup for each day containing 5 sequential steps.

**Requirements:**

1. **Dependency Management:**
   - Add `evidently`, `psycopg` (or `psycopg2-binary`), `pandas`, `joblib` to `pyproject.toml` if they are not already there.

2. **Task Module (`src/monitoring/tasks.py`):**
   - Create a module with 5 functions decorated with `@task` (Airflow TaskFlow API).
   - Ensure `data/temp/` directory is created if it doesn't exist.

   **The 5 Tasks:**
   1. **`fetch_data(date_str, **kwargs)`:**
      - Load `val.parquet`from the related s3 bucket.
      - Convert Timestamp to datetime. Filter rows matching `date_str`.
      - pass the filtered data to next task.

   2. **`preprocess_data( **kwargs)`:**
      - get the chunk
      - Add time features: `year`, `month`, `day`, `dayofweek`, `is_weekend` (matching training logic).
      - pass to next task
   3. **`generate_predictions(**kwargs)`:**
      - Load the chunk.
      - Load the model from the s3 bucket. there may be several models in the s3 bucket, define a variable related to airflow model id, and get the model id from the .env and read the model .pkl file from the s3 bucket directly.
      - Predict. Add `prediction` column.
      - pass to the next task.
   4. **`calculate_metrics(**kwargs)`:**
      - Load the prediction chunk (Current).
      - Load `train.parquet` from the s3 bucket(Reference).
      - Run Evidently `Report` (Drift + Missing Values).
      - Return a **Dictionary** of metrics (e.g., `prediction_drift`, `share_missing_values`).
   5. **`log_metrics(metrics_dict, date_str, **kwargs)`:**
      - Connect to Postgres (`host=mlflow-postgres`, `user=postgres`, `db=monitoring`).
      - Create table `monitoring_metrics` if missing.
      - Insert the metrics.
      - **Crucial:** `time.sleep(20)` to simulate the delay.

3. **The DAG (`dags/monitoring_simulation.py`):**
   - **Config:** Start Date: `2024-09-14`, End Date: `2024-11-09`.
   - **Structure:**
     - Use `sys.path.append` to find `src`.
     - Use a loop over the date range.
     - Inside the loop, create a `TaskGroup(group_id=f"day_{date_str}")`.
     - Call the 5 tasks sequentially: `path1 = fetch(...)` -> `path2 = preprocess(path1)` ...
     - **Enforce Order:** Ensure Day N finishes before Day N+1 starts (`previous_tg >> current_tg`).

**Constraints:**
- Use `psycopg` context managers for safe DB connections.
- Ensure the DAG has `schedule=None` (Manual trigger).

**Definition of Done:**
- Airflow UI shows a graph of ~55 connected TaskGroups (one for each day).
- Triggering the DAG runs successfully, populating the `monitoring_metrics` table sequentially every 20 seconds.
