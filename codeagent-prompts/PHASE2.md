# Implementation of Data Pipeline and AutoML Training

**Context:**
We are implementing the core MLOps pipeline for the "Smart Logistics Supply Chain" project.
The goal is to move from raw data to a trained model registered in MLflow, orchestrated by Airflow.

**Requirements:**

1. **Environment & Dependencies:**
   - Use `uv` or `poetry` to add: `kagglehub`, `pandas`, `scikit-learn`, `mlflow`, `flaml`, `dvc[s3]`, `boto3`, `pyarrow`.
   - Ensure `MLFLOW_TRACKING_URI` and AWS credentials (for LocalStack) are pulled from `.env`.

2. **Data Ingestion (`src/data_ingestion/`):**
   - Create `ingest.py`: Download dataset using `kagglehub`.
   - Upload the raw `.csv` to the S3 bucket (configured via `AWS_S3_BUCKET` env var).
   - Use DVC to track the local copy in `data/raw/logistics.csv`.

3. **Feature Engineering & Splitting (`src/feature_engineering/`):**
   - Create `preprocess.py`:
     - Convert `Timestamp` to datetime.
     - **Prevent Leakage:** Sort by `Timestamp`. Use the first 70% for train, 15% for val, 15% for test.
     - Features: Extract `hour`, `day_of_week`, `month` from `Timestamp`.
     - Handle categorical variables: `Shipment_Status`, `Traffic_Status`, `Logistics_Delay_Reason` (use Target Encoding or One-Hot).
     - Save splits as `.parquet` to `data/processed/` and sync to S3.

4. **Model Training (`src/model_training/`):**
   - Create `train.py`:
     - Use **FLAML** (AutoML) to find the best classifier for `Logistics_Delay`.
     - Constraints: Time budget = 600s, Metric = 'roc_auc'.
     - **MLflow Integration:** - Start an MLflow run.
       - Log parameters, best model type, and metrics (ROC-AUC, F1-Score).
       - Save and register the model in the MLflow Model Registry as "LogisticsDelayModel".

5. **Airflow Orchestration (`dags/supply_chain_dag.py`):**
   - Update the DAG to include three tasks using `PythonOperator`:
     - `ingest_task` -> `preprocess_task` -> `train_task`.
   - Ensure the DAG handles retries and logs clearly.

6. **Testing:**
   - Add a test in `tests/test_pipeline.py` that verifies the data split (e.g., check that max(train_ts) < min(test_ts)).

**Technical Constraints:**
- Use `src` layout for imports (e.g., `from src.utils import logger`).
- All S3 interactions should support a custom `endpoint_url` for LocalStack.

**Definition of Done:**
- [ ] Running `make pipeline` (add this to Makefile) triggers the Airflow DAG.
- [ ] Data splits exist in S3 (LocalStack).
- [ ] MLflow UI shows a successful run with artifacts and a registered model.
- [ ] `.dvc` files are updated to reflect the new data.
