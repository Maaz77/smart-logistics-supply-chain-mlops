# Minimal-Touch Airflow Integration

**Context:**
We have a working MLOps infra (LocalStack, MLflow, Postgres). I need to add Airflow for orchestration WITHOUT modifying the current service configurations. This must be a "plug-and-play" addition.

**Requirements:**

1. **New Airflow Container Setup:**
   - Create `deployment/docker/Dockerfile.airflow` based on `apache/airflow:2.7.1-python3.10`.
   - Install ONLY the necessary libs to run the ml pipeline:
   - Set `PYTHONPATH=/opt/airflow`.

2. **Isolated Compose File (`docker-compose.airflow.yaml`):**
   - Define a minimal Airflow setup: `airflow-webserver`, `airflow-scheduler`, and `airflow-db` (Postgres).
   - **Crucial:** Use the `networks` section to join the **existing** network from the main `docker-compose.yaml`.
   - Define the existing network as `external`. Example:
     ```yaml
     networks:
       default:
         external: true
         name: <YOUR_EXISTING_NETWORK_NAME>
     ```
   - **Volumes:** Mount `./dags` to `/opt/airflow/dags` and `./src` to `/opt/airflow/src`.

3. **Zero-Touch Config:**
   - Do NOT modify the existing `docker-compose.yaml` or `mlflow` settings.
   - Use environment variables in the new Airflow compose to point to the existing services:
     - `AIRFLOW__CORE__SQL_ALCHEMY_CONN` (pointing to the new airflow-db)
     - `MLFLOW_TRACKING_URI=http://mlflow:5000`
     - `AWS_ENDPOINT_URL=http://localstack:4566`

4. **Makefile Update:**
   - Add `make airflow-up`: Runs `docker compose -f docker-compose.airflow.yaml up -d`.
   - Add `make airflow-down`: Runs `docker compose -f docker-compose.airflow.yaml down`.

**Definition of Done:**
- [ ] The existing MLflow and LocalStack services remain running and unaffected.
- [ ] Airflow starts up and can "see" the `mlflow` container over the network.
- [ ] The `supply_chain_dag` is parsed correctly and can trigger a test task that imports a function from `src`.
