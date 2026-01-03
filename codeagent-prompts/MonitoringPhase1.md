
You are a Senior DevOps Engineer. Your task is to implement the "Monitoring Infrastructure" layer for an existing MLOps project.

**Context:**
- We currently have a `docker-compose.yaml` with a service `mlflow-postgres` (PostgreSQL 13+) serving the `mlflow` database.
- We want to add **Evidently** (metrics) and **Grafana** (dashboards) without adding a new Postgres container.
- We want to enable these services optionally via a specific Makefile target.

**Requirements:**

1. **Database Initialization Strategy:**
   - Create a script `scripts/infra/init_monitoring_db.sh`.
   - It should connect to the `mlflow-postgres` container and create a database named `monitoring` if it does not exist.
   - Use `psql` commands. Handle cases where the DB already exists gracefully (idempotency).

2. **Grafana Configuration (IaC):**
   - Create folder structure: `config/grafana/provisioning/datasources/`.
   - Create `datasource.yml` that configures a PostgreSQL datasource named "Evidently_Monitoring".
   - **Host:** `mlflow-postgres:5432`
   - **Database:** `monitoring`
   - **User/Password:** Use env vars `${POSTGRES_USER}` and `${POSTGRES_PASSWORD}` (default to `postgres`/`postgres` if not set, but prefer env vars).
   - **SSL Mode:** disable.

3. **Docker Compose Files:**
   - **`docker-compose.monitoring.yaml`**: Create this new file.
     - Service: `grafana`
       - Image: `grafana/grafana:latest`
       - Ports: `3000:3000`
       - Volumes:
         - Mount `./config/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources`
         - `grafana_data:/var/lib/grafana` (named volume for persistence)
       - Environment:
         - `GF_SECURITY_ADMIN_USER=admin`
         - `GF_SECURITY_ADMIN_PASSWORD=admin`
     - Service: `adminer`
       - Image: `adminer`
       - Ports: `8081:8080`
       - Depends on: `mlflow-postgres` (from the main compose file, note: this might require network bridging if not carefully handled. Ensure both compose files use the same network `mlops_network` declared as "external" or shared).

   - **`docker-compose.yaml`** (Update):
     - Ensure the default network is named explicitly (e.g., `mlops_network`) so the monitoring compose file can join it.

4. **Makefile Updates:**
   - Add target `init-db`: Executes the `init_monitoring_db.sh` script (e.g., via `docker exec` if the container is running, or a local script connecting to localhost:5432). Prefer `docker exec -it mlflow-postgres ...` for reliability.
   - Add target `monitoring`: Runs `docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d`.
   - Add target `monitoring-down`: Stops the monitoring services.

5. **Documentation:**
   - Update `README.md` with a "Monitoring" section explaining how to access Grafana (localhost:3000) and Adminer (localhost:8081).

**Constraints:**
- Do not break the existing MLflow or Airflow setups.
- Ensure the `monitoring` database user has full privileges on the `monitoring` DB.
- Use the existing `.env` file for credentials if available.

**Definition of Done:**
- `make monitoring` brings up Grafana and Adminer.
- `make init-db` successfully creates the `monitoring` database in the existing Postgres container.
- Grafana opens on port 3000 and the Postgres datasource "Evidently_Monitoring" acts as "Health Check: OK".
