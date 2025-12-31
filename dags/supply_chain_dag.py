from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "mlops_team",
    "depends_on_past": False,
    "start_date": datetime(2023, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "supply_chain_pipeline",
    default_args=default_args,
    description="Smart Logistics Supply Chain ML Pipeline",
    schedule_interval=timedelta(days=1),
    catchup=False,
)


def ingest_data():
    print("Ingesting data...")


def validate_data():
    print("Validating data...")


def engineer_features():
    print("Engineering features...")


def train_model():
    print("Training model...")


def evaluate_model():
    print("Evaluating model...")


ingest_task = PythonOperator(
    task_id="ingest_data",
    python_callable=ingest_data,
    dag=dag,
)

validate_task = PythonOperator(
    task_id="validate_data",
    python_callable=validate_data,
    dag=dag,
)

feature_task = PythonOperator(
    task_id="engineer_features",
    python_callable=engineer_features,
    dag=dag,
)

train_task = PythonOperator(
    task_id="train_model",
    python_callable=train_model,
    dag=dag,
)

eval_task = PythonOperator(
    task_id="evaluate_model",
    python_callable=evaluate_model,
    dag=dag,
)

ingest_task >> validate_task >> feature_task >> train_task >> eval_task
