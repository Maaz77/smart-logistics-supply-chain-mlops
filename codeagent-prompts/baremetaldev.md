### CODING_AGENT_PROMPT: Pivot to Bare-Metal Development Workflow

**Context:** We are simplifying the development environment. We are removing the `dev` container layer. All Python scripts (ingestion, training, etc.) will now run directly on the host machine using the Poetry virtual environment. LocalStack and Postgres will remain in Docker as "Background Services."

**Task:**
Refactor the repository to support a bare-metal execution model while maintaining professional MLOps standards.

**1. Infrastructure Cleanup:**
- **Delete:** `deployment/docker/Dockerfile` and `deployment/docker/docker-compose.dev.yaml`.
- **Modify `deployment/docker/docker-compose.yaml`:**
    - Ensure all necessary services (LocalStack, Postgres, MLflow) are in this single file.
    - Ensure ports for all services are mapped to `localhost` (e.g., `4566:4566`, `5432:5432`, `5001:5000`).
    - Remove any `networks` configurations that were only used for inter-container communication if they interfere with host access.

**2. Makefile Refactor:**
- **Update `infra-up`:** Change to `docker compose -f deployment/docker/docker-compose.yaml up -d --wait`.
- **Update `run` target:** if we dont need it anymore, delete it.
**3. Python Code & Environment Alignment:**
- **Update `src/utils/common.py`:** - Modify connection logic for S3/Postgres. Since scripts run on bare metal, they should always point to `localhost` instead of container names like `localstack` or `postgres`.
- **Update `.env`:** Ensure `AWS_ENDPOINT_URL=http://localhost:4566` and `DB_HOST=localhost`.

**4. Documentation:**
- Update `README.md` to reflect that Docker is now only used for infrastructure, not for running code.
- Update the "Prerequisites" section to emphasize local Python 3.12 and Poetry installation.

**Constraints:**
- Ensure `make setup` still correctly initializes the local virtual environment and pre-commit hooks.

**Definition of Done:**
1. `make infra-up` starts the cloud services.
2. The script successfully connects to LocalStack S3 and Postgres at `localhost`.
