# Smart Logistics & Supply Chain ML

A production-grade MLOps repository for optimizing supply chain logistics using machine learning.

## 🚀 Quick Start

```bash
# 1. Activate conda environment
conda activate MLOpspy312

# 2. Install dependencies
make setup

# 3. Start infrastructure (LocalStack, Postgres, MLflow)
make infra-up

# 4. Initialize Terraform resources
make infra-init

# 5. Run your scripts directly
python src/your_script.py
```

## 📋 Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.12+ | Runtime |
| Poetry | 1.7+ | Dependency management |
| Docker | 24+ | Infrastructure services |
| Terraform | 1.5+ | IaC (via tflocal) |

## 📦 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Machine (Bare Metal)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  Python Scripts (run directly with Poetry)               │  │
│   │  • src/data_ingestion/                                   │  │
│   │  • src/model_training/                                   │  │
│   │  • src/feature_engineering/                              │  │
│   └──────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                          │ localhost                             │
│                          ▼                                       │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  Docker Infrastructure (make infra-up)                   │  │
│   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │  │
│   │  │ LocalStack  │ │ PostgreSQL  │ │   MLflow    │        │  │
│   │  │ :4566       │ │ :5432       │ │ :5001       │        │  │
│   │  └─────────────┘ └─────────────┘ └─────────────┘        │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Available Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make setup` | Install Poetry deps, pre-commit hooks, init Terraform |
| `make quality` | Run ruff + mypy + pytest |
| `make format` | Auto-format code with ruff |
| `make infra-up` | Start LocalStack, Postgres, MLflow |
| `make infra-down` | Stop all Docker services |
| `make infra-init` | Create S3 buckets and IAM roles via Terraform |
| `make infra-logs` | Show logs from infrastructure services |
| `make s3-sync` | Manual bidirectional sync (Local ↔ S3) |
| `make clean` | Clean Python caches (Safe: keeps infra state) |
| `make reset-infra` | **Destructive**: Delete all LocalStack & Terraform state |
| `make monitoring` | Start monitoring services (Grafana + Adminer) |
| `make monitoring-down` | Stop monitoring services |

## 🌐 Service URLs (after `make infra-up`)

| Service | URL | Purpose |
|---------|-----|---------|
| LocalStack | http://localhost:4566 | AWS emulation (S3, IAM) |
| PostgreSQL | localhost:5432 | Unified database for MLflow, Airflow, Monitoring, and Serving |
| MLflow UI | http://localhost:5001 | Experiment tracking |
| Airflow UI | http://localhost:8080 | Workflow orchestration |
| Grafana | http://localhost:3000 | Monitoring dashboards (optional) |
| Adminer | http://localhost:8081 | Database admin UI (optional) |

## 📊 Monitoring

The project includes optional monitoring infrastructure using **Grafana** (for dashboards) and **Adminer** (for database administration). These services use the unified `mlops-postgres` container and connect to the `monitoring` database for Evidently metrics.

### Setup Monitoring

```bash
# 1. Ensure infrastructure is running
make infra-up

# 2. Ensure MLOps services are running (creates monitoring database automatically)
make ml-services-up

# 3. Start monitoring services
make monitoring
```

### Access Monitoring Services

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  - The PostgreSQL datasource "Evidently_Monitoring" is automatically configured to connect to the `monitoring` database

- **Adminer**: http://localhost:8081
  - System: `PostgreSQL`
  - Server: `postgres` (or `localhost:5432` from host)
  - Username: `MLOps_Full_Postgres` (or value from `POSTGRES_USER` env var)
  - Password: `MLOps_Full_Postgres` (or value from `POSTGRES_PASSWORD` env var)
  - Database: `monitoring` (or `mlflow` for MLflow data, `airflow` for Airflow metadata, `serving` for serving logs)

### Stop Monitoring

```bash
make monitoring-down
```

**Note**: The monitoring database persists in the unified `mlops-postgres` container alongside the `mlflow` and `airflow` databases. To remove it, you would need to manually drop it via Adminer or `psql`.

## 💾 Persistent Storage (S3 Buckets & Local Folders)

The infrastructure uses LocalStack to simulate AWS S3 buckets. Data is synced bidirectionally with local folders, ensuring persistence across container restarts.

| S3 Bucket | Local Folder | Purpose |
|-----------|--------------|----------|
| `s3://smart-logistics-data` | `./data/` | Raw & processed datasets |
| `s3://mlflow-model-registry` | `./models/` | MLflow model artifacts |

| Local Folder | Purpose |
|--------------|---------|
| `./mlops_services/postgres_data/` | PostgreSQL data (mlflow, airflow, monitoring, serving databases) |

**How it works:**
- On `make infra-up`: Starts Docker services (LocalStack, PostgreSQL, MLflow)
- On `make infra-init`: **Terraform creates S3 buckets** and syncs local folders **to** S3
- On `make s3-sync`: Manual bidirectional sync between local folders and S3
- On `make infra-down`: Final sync from S3 **to** local before shutdown
- After shutdown: `data/`, `models/`, `mlops_services/postgres_data/` persist on disk

## 📁 Project Structure

```
Smart-Logistics-Supply-Chain-ML/
├── src/                    # Source code (run directly)
│   ├── data_ingestion/     # Data retrieval
│   ├── data_validation/    # Schema validation
│   ├── feature_engineering/# Feature extraction
│   ├── model_training/     # Training pipelines
│   ├── model_evaluation/   # Metrics & validation
│   └── utils/              # Shared utilities
├── data/                   # 📦 Synced with s3://smart-logistics-data
├── models/                 # 📦 Synced with s3://mlflow-model-registry
├── mlops_services/
│   └── postgres_data/      # 📦 PostgreSQL data persistence (mlflow, airflow, monitoring, serving)
├── deployment/docker/      # Docker Compose (infrastructure only)
├── infrastructure/terraform/ # IaC for LocalStack
├── config/grafana/        # Grafana provisioning configs
├── scripts/infra/         # Infrastructure initialization scripts
├── tests/                  # Pytest test suite
├── configs/                # YAML configurations
└── notebooks/              # Jupyter notebooks
```

## 🔄 Development Workflow

### 1. Start Infrastructure
```bash
make infra-up      # Start Docker services
make infra-init    # Create AWS resources in LocalStack
```

### 2. Run Your Code
```bash
# Run any script directly with Poetry
python src/utils/common.py
python src/data_ingestion/ingest.py

# Or use poetry run
poetry run python src/model_training/train.py
```

### 3. Quality Checks
```bash
make quality       # Runs: ruff, mypy, pytest
make format        # Auto-fix formatting
```

### 4. Cleanup
```bash
make infra-down    # Stop containers
make clean         # Full cleanup
```

## 🔧 Environment Configuration

Create a `.env` file in the project root (see `.env.example`):

```bash
# AWS/LocalStack
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1

# LocalStack Pro (optional)
LOCALSTACK_TOKEN=your-token-here

# S3 Bucket Names
S3_DATA_BUCKET=smart-logistics-data
S3_MODEL_REGISTRY_BUCKET=mlflow-model-registry

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=MLOps_Full_Postgres
POSTGRES_PASSWORD=MLOps_Full_Postgres
POSTGRES_DB=mlflow

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5001
MLFLOW_S3_ENDPOINT_URL=http://localhost:4566
MLFLOW_ARTIFACT_ROOT=s3://mlflow-model-registry
```

## 🏗️ MLOps Stack

| Component | Technology |
|-----------|------------|
| Package Manager | Poetry |
| Experiment Tracking | MLflow |
| Infrastructure | Terraform + LocalStack |
| Linting | Ruff |
| Type Checking | MyPy |
| Testing | Pytest |
| CI/CD | GitHub Actions |

## 🧪 Testing

```bash
# Run all quality checks
make quality

# Run tests only
pytest tests/ -v
```

## 📄 License

MIT License
