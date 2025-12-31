### CODING_AGENT_PROMPT: Phase 1 - Production Foundation & GitHub Actions CI

**Context:** You are building a professional MLOps environment for "Smart-Logistics-Supply-Chain-ML". We require a persistent MLflow (Postgres backend), LocalStack (Student Pack features), Terraform for IaC, and a GitHub Actions CI pipeline.

**Task:**
Generate the following core files and structure. Ensure all paths match the provided `PROJECT_STRUCTURE.md`.

**1. Infrastructure & Orchestration (deployment/docker/):**
- **`docker-compose.yaml`**: Define the base network and `localstack` (v3+) with persistence enabled (`PERSISTENCE=1`) and volume mount to `./.localstack`.
- **`docker-compose.dev.yaml`**:
    - **`postgres`**: Configured as the MLflow backend store.
    - **`mlflow`**: Depends on `postgres` and `localstack`. Use `postgresql://` for metadata and `s3://ml-artifacts` for artifacts. Set `MLFLOW_S3_ENDPOINT_URL=http://localstack:4566`.
- **`Dockerfile`**: Multi-stage build (stage `base` with poetry, stage `dev` with all dependencies).

**2. Infrastructure as Code (infrastructure/terraform/):**
- **`provider.tf`**: Configure AWS provider to point all endpoints (S3, IAM, STS, RDS) to `http://localhost:4566`. Enable `s3_use_path_style`.
- **`main.tf`**: Provision an S3 bucket `smart-logistics-artifacts` and a placeholder IAM role `mlflow-s3-access-role`.

**3. GitHub Actions CI (.github/workflows/ci.yml):**
- Create a workflow named "MLOps CI" triggered on `push` and `pull_request`.
- **Job: Lint-and-Test**:
    - Runs on `ubuntu-latest`.
    - Steps: Checkout code, Setup Python (3.12), Install dependencies (Poetry).
    - Run `ruff check .` and `ruff format --check .`.
    - Run `mypy src/`.
- **Job: Infra-Validation**:
    - Steps: Setup Terraform, Start LocalStack (using `localstack/localstack-github-action@main`), Run `terraform init` and `terraform validate`.

**4. Quality & Dependencies:**
- **`pyproject.toml`**: Include `mlflow`, `psycopg2-binary`, `boto3`, `pandas`, `scikit-learn`. Dev deps: `ruff`, `mypy`, `pytest`, `pytest-docker`.
- **`.pre-commit-config.yaml`**: Configure `ruff` and `mypy` hooks.
- **`Makefile`**:
    - `setup`: Install poetry, pre-commit, and terraform init.
    - `infra-up`: Start docker-compose and wait for health.
    - `infra-init`: Run `terraform apply -auto-approve` against LocalStack.
    - `test`: Run pytest.
    - `clean`: Stop containers and wipe `.localstack/` data.

**Constraints:**
- Use the `src` layout.
- Use `http://localstack:4566` for container-to-container comms and `http://localhost:4566` for host-to-container comms.
- NO hardcoded secrets. Use `.env.example`.

**Definition of Done:**
1. `make setup && make infra-up` starts MLflow with a Postgres backend.
2. `make infra-init` creates the S3 bucket in LocalStack.
3. The `.github/workflows/ci.yml` is syntactically correct and covers linting and infra validation.
