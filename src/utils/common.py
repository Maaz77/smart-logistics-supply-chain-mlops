"""
Common utility functions for Smart Logistics Supply Chain ML.

This module provides shared utilities used across the project including:
- Configuration file handling
- Directory management
- Service endpoint resolution (bare-metal mode: always localhost)
"""

import logging
import os
from typing import Any

import yaml

# Configure logging
logger = logging.getLogger(__name__)


def read_yaml(path_to_yaml: str) -> dict[Any, Any]:
    """Reads a yaml file and returns its content as a dictionary.

    Args:
        path_to_yaml: Path to the YAML configuration file.

    Returns:
        Dictionary containing the YAML file contents.

    Raises:
        FileNotFoundError: If the YAML file doesn't exist.
        yaml.YAMLError: If the YAML file is malformed.
    """
    with open(path_to_yaml) as yaml_file:
        content = yaml.safe_load(yaml_file)
    return content


def create_directories(path_to_directories: list[str]) -> None:
    """Creates directories if they do not exist.

    Args:
        path_to_directories: List of directory paths to create.
    """
    for path in path_to_directories:
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created directory at: {path}")


def get_size(path: str) -> str:
    """Returns file size in KB.

    Args:
        path: Path to the file.

    Returns:
        Human-readable string with file size in KB.
    """
    size_in_kb = round(os.path.getsize(path) / 1024)
    return f"~ {size_in_kb} KB"


# ============================================
# Service Configuration (Bare-Metal Mode)
# ============================================
# All services run in Docker but are accessed via localhost


def get_localstack_endpoint() -> str:
    """Returns the LocalStack endpoint URL.

    In bare-metal mode, LocalStack is accessed via localhost.

    Returns:
        LocalStack endpoint URL (http://localhost:4566)
    """
    return os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")


def get_mlflow_tracking_uri() -> str:
    """Returns the MLflow tracking URI.

    In bare-metal mode, MLflow is accessed via localhost:5001.

    Returns:
        MLflow tracking URI
    """
    return os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")


def get_postgres_connection_string() -> str:
    """Returns the PostgreSQL connection string.

    In bare-metal mode, Postgres is accessed via localhost.

    Returns:
        PostgreSQL connection string.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "mlflow")
    password = os.getenv("POSTGRES_PASSWORD", "mlflow")
    database = os.getenv("POSTGRES_DB", "mlflow")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_s3_client():
    """Returns a boto3 S3 client configured for LocalStack.

    Returns:
        boto3 S3 client configured for LocalStack endpoint.
    """
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=get_localstack_endpoint(),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


# ============================================
# Module self-test
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("Smart Logistics - Common Utilities Test")
    print("=" * 50)
    print(f"LocalStack endpoint: {get_localstack_endpoint()}")
    print(f"MLflow tracking URI: {get_mlflow_tracking_uri()}")
    print(f"PostgreSQL connection: {get_postgres_connection_string()}")
    print("=" * 50)
    print("✓ All utilities loaded successfully!")
