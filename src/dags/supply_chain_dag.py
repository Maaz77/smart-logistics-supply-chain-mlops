"""
Airflow DAG for Smart Logistics Supply Chain ML Pipeline.

Orchestrates: Data Ingestion -> Preprocessing -> Model Training
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "mlops_team",
    "depends_on_past": False,
    "start_date": datetime(2023, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "supply_chain_pipeline",
    default_args=default_args,
    description="Smart Logistics Supply Chain ML Pipeline",
    schedule_interval=None,
    catchup=False,
    tags=["ml", "logistics", "pipeline"],
)


def ingest_data():
    """Run data ingestion from Kaggle to S3."""
    from src.ml_pipeline import run_ingestion

    result = run_ingestion()
    print(f"Ingestion result: {result}")
    return result


def preprocess_data():
    """Run feature engineering and data splitting."""
    from src.ml_pipeline import run_preprocessing

    result = run_preprocessing()
    print(f"Preprocessing result: {result}")
    return result


def train_model():
    """Train model using sklearn and register with MLflow."""
    from src.ml_pipeline import run_training

    result = run_training()
    print(f"Training result: {result}")
    return result


ingest_task = PythonOperator(
    task_id="ingest_data",
    python_callable=ingest_data,
    dag=dag,
)

preprocess_task = PythonOperator(
    task_id="preprocess_data",
    python_callable=preprocess_data,
    dag=dag,
)

train_task = PythonOperator(
    task_id="train_model",
    python_callable=train_model,
    dag=dag,
)

# Define task dependencies
ingest_task >> preprocess_task >> train_task
