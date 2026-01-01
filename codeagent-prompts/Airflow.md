### CODING_AGENT_PROMPT: Airflow Containerization and Orchestration

**Context:**
We need to move the ML pipeline from a manual `make pipeline` command to a fully containerized Airflow orchestration. The environment must be able to interact with LocalStack (S3) and the existing MLflow service.

**Requirements:**

1. **Docker Integration:**
   - Create `deployment/docker/Dockerfile.airflow` based on `apache/airflow:2.7.1-python3.10`.
   - The Dockerfile must:
     - Install `gcc` and `python3-dev` (required for some ML libs).
     - Copy `pyproject.toml` and `poetry.lock` (if exists) or `requirements.txt`.
     - Install project dependencies into the airflow user space.
     - Set `PYTHONPATH=/opt/airflow` to ensure `src` is importable.

2. **Docker Compose Update:**
   - Add the following services to the main `docker-compose.yaml`:
     - `airflow-db`: Postgres 13 image for Airflow metadata.
     - `airflow-init`: A one-off service to run `airflow db init`.
     - `airflow-webserver`: Expose on port `8080`.
     - `airflow-scheduler`: Responsible for triggering the DAG.
   - **Volumes:** Mount `./dags:/opt/airflow/dags`, `./src:/opt/airflow/src`, and `./data:/opt/airflow/data`.
   - **Network:** Ensure all airflow services share the same network as `localstack` and `mlflow`.

3. **Airflow Configuration:**
   - Use environment variables in `docker-compose` to configure:
     - `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`
     - `AWS_ENDPOINT_URL=http://localstack:4566`
     - `MLFLOW_TRACKING_URI=http://mlflow:5000`
     - `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`, `AWS_DEFAULT_REGION=us-east-1`

4. **DAG Refinement (`dags/supply_chain_dag.py`):**
   - Ensure the `PythonOperator` tasks correctly call the functions in:
     - `src.ml_pipeline.ingest.main`
     - `src.ml_pipeline.preprocess.main`
     - `src.ml_pipeline.train.main`

5. **Makefile Update:**
   - Add a target `make up-airflow` to start these services.
   - Add a target `make airflow-login` to output the default credentials (admin/admin).

**Definition of Done:**
- [ ] `docker-compose up` starts the Airflow UI on `localhost:8080`.
- [ ] The `supply_chain_pipeline` DAG is visible in the UI.
- [ ] A manual trigger of the DAG successfully completes all three stages (Ingest, Preprocess, Train).
- [ ] Logs in the Airflow UI show the model being registered in MLflow.
