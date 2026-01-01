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
| `make clean` | Remove containers, caches, and LocalStack data |

## 🌐 Service URLs (after `make infra-up`)

| Service | URL | Purpose |
|---------|-----|---------|
| LocalStack | http://localhost:4566 | AWS emulation (S3, IAM) |
| PostgreSQL | localhost:5432 | MLflow backend store |
| MLflow UI | http://localhost:5001 | Experiment tracking |

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
├── data/                   # Data directory (DVC managed)
├── deployment/docker/      # Docker Compose (infrastructure only)
├── infrastructure/terraform/ # IaC for LocalStack
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

Create a `.env` file in the project root:

```bash
# AWS/LocalStack
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1

# LocalStack Pro (optional)
LOCALSTACK_TOKEN=your-token-here

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mlflow
POSTGRES_PASSWORD=mlflow
POSTGRES_DB=mlflow

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5001
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
