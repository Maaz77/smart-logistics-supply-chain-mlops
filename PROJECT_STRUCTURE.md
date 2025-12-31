# Project Structure

This document provides a complete overview of the **Smart-Logistics-Supply-Chain-ML** project structure, including all files, folders, and hidden files.

```
Smart-Logistics-Supply-Chain-ML/
│
├── .dvc/                                  # DVC (Data Version Control) configuration
│   ├── config                             # DVC configuration file
│   └── tmp/                               # DVC temporary files
│       └── btime                          # Build time tracking
│
├── .github/                               # GitHub configuration
│   └── workflows/                         # GitHub Actions workflows
│       └── lint.yaml                      # Linting workflow configuration
│
├── .pytest_cache/                         # Pytest cache directory
│   ├── .gitignore                         # Git ignore for cache
│   ├── CACHEDIR.TAG                       # Cache directory tag
│   ├── README.md                          # Pytest cache documentation
│   └── v/                                 # Version cache
│       └── cache/                         # Cache storage
│           └── nodeids                    # Cached node IDs
│
├── .dvcignore                             # DVC ignore patterns
├── .env                                   # Environment variables (local, not committed)
├── .env.example                           # Example environment variables template
├── .gitignore                             # Git ignore patterns
├── .pre-commit-config.yaml                # Pre-commit hooks configuration
│
├── codeagent-prompts/                     # Code agent prompt templates
│   └── MLOps_scaffold_prompt.md           # MLOps scaffolding prompt
│
├── configs/                               # Configuration files
│   └── config.yaml                        # Main configuration file
│
├── dags/                                  # Apache Airflow DAGs
│   └── supply_chain_dag.py                # Supply chain pipeline DAG
│
├── data/                                  # Data directory
│   ├── external/                          # External data sources
│   │   └── .gitkeep                       # Placeholder to track empty dir
│   ├── processed/                         # Processed/transformed data
│   │   └── .gitkeep                       # Placeholder to track empty dir
│   └── raw/                               # Raw data files
│       └── .gitkeep                       # Placeholder to track empty dir
│
├── deployment/                            # Deployment configurations
│   ├── docker/                            # Docker configurations
│   │   ├── Dockerfile                     # Docker image definition
│   │   └── docker-compose.yaml            # Docker Compose configuration
│   └── k8s/                               # Kubernetes configurations
│       └── deployment.yaml                # K8s deployment manifest
│
├── logs/                                  # Application logs
│   └── .gitkeep                           # Placeholder to track empty dir
│
├── models/                                # Trained model artifacts
│   └── .gitkeep                           # Placeholder to track empty dir
│
├── notebooks/                             # Jupyter notebooks (empty)
│
├── src/                                   # Source code
│   ├── __init__.py                        # Package initialization
│   ├── __pycache__/                       # Python bytecode cache
│   │   └── __init__.cpython-312.pyc       # Compiled bytecode
│   │
│   ├── data_ingestion/                    # Data ingestion module
│   │   └── __init__.py                    # Module initialization
│   │
│   ├── data_validation/                   # Data validation module
│   │   └── __init__.py                    # Module initialization
│   │
│   ├── feature_engineering/               # Feature engineering module
│   │   └── __init__.py                    # Module initialization
│   │
│   ├── model_evaluation/                  # Model evaluation module
│   │   └── __init__.py                    # Module initialization
│   │
│   ├── model_training/                    # Model training module
│   │   └── __init__.py                    # Module initialization
│   │
│   └── utils/                             # Utility functions
│       ├── __init__.py                    # Module initialization
│       ├── common.py                      # Common utility functions
│       └── __pycache__/                   # Python bytecode cache
│           ├── __init__.cpython-312.pyc   # Compiled bytecode
│           └── common.cpython-312.pyc     # Compiled bytecode
│
├── tests/                                 # Test suite
│   ├── __init__.py                        # Test package initialization
│   ├── test_common.py                     # Tests for common utilities
│   └── __pycache__/                       # Python bytecode cache
│       ├── __init__.cpython-312.pyc       # Compiled bytecode
│       └── test_common.cpython-312-pytest-9.0.2.pyc  # Compiled test bytecode
│
├── poetry.lock                            # Poetry dependency lock file
├── pyproject.toml                         # Python project configuration
├── PROJECT_STRUCTURE.md                   # This file - project structure documentation
└── README.md                              # Project documentation
```

---

## Directory Overview

| Directory/File | Purpose |
|----------------|---------|
| `.dvc/` | Data Version Control configuration and cache |
| `.github/` | GitHub Actions CI/CD workflows |
| `.pytest_cache/` | Pytest execution cache |
| `codeagent-prompts/` | AI code agent prompt templates |
| `configs/` | Application configuration files |
| `dags/` | Apache Airflow DAG definitions |
| `data/` | Raw, processed, and external data storage |
| `deployment/` | Docker and Kubernetes deployment configs |
| `logs/` | Application log files |
| `models/` | Trained ML model artifacts |
| `notebooks/` | Jupyter notebooks for exploration |
| `src/` | Main source code packages |
| `tests/` | Unit and integration tests |

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `.dvcignore` | Patterns for DVC to ignore |
| `.env` | Local environment variables (secrets, API keys) |
| `.env.example` | Template for required environment variables |
| `.gitignore` | Patterns for Git to ignore |
| `.pre-commit-config.yaml` | Pre-commit hook configurations |
| `pyproject.toml` | Python project metadata and dependencies |
| `poetry.lock` | Locked dependency versions |

---

## Source Code Modules (`src/`)

| Module | Purpose |
|--------|---------|
| `data_ingestion/` | Data loading and acquisition logic |
| `data_validation/` | Data quality checks and validation |
| `feature_engineering/` | Feature transformation and creation |
| `model_training/` | ML model training pipelines |
| `model_evaluation/` | Model performance evaluation |
| `utils/` | Shared utility functions |

---

*Last updated: 2025-12-31*
