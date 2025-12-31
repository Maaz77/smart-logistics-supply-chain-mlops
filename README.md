# Smart Logistics & Supply Chain ML

A production-grade MLOps repository for optimizing supply chain logistics using machine learning.

## Project Structure

- `data/`: Contains raw, intermediate, and processed data (managed by DVC).
- `models/`: Model artifacts and versions.
- `notebooks/`: Jupyter notebooks for EDA and experimentation.
- `src/`: Core source code for the ML pipeline.
  - `data_ingestion/`: Scripts for data retrieval.
  - `data_validation/`: Schema validation and data drift detection.
  - `feature_engineering/`: Trasformation and feature extraction.
  - `model_training/`: Training scripts and hyperparameter tuning.
  - `model_evaluation/`: Performance metrics and validation.
- `dags/`: Airflow DAGs for pipeline orchestration.
- `deployment/`: Docker and Kubernetes configuration files.
- `configs/`: YAML configurations for training and logging.
- `tests/`: Unit and integration tests.

## Setup Instructions

1. **Environment Setup**:
   ```bash
   conda activate MLOpspy312
   poetry install
   ```

2. **DVC Initialization**:
   ```bash
   dvc pull  # Once remote is configured
   ```

3. **Running the Pipeline**:
   The pipeline can be orchestrated via Airflow or run as individual scripts in `src/`.

4. **Linting and Formatting**:
   ```bash
   ruff check .
   black .
   ```

## MLOps Stack

- **Version Control**: Git & DVC
- **Tracking**: MLflow
- **Orchestration**: Apache Airflow
- **Containerization**: Docker
- **Deployment**: Kubernetes
- **CI/CD**: GitHub Actions
