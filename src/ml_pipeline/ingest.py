"""
Data Ingestion Module for Smart Logistics Supply Chain.

Downloads the dataset from Kaggle and uploads directly to S3.
"""

import logging
from pathlib import Path

import kagglehub

from src.ml_pipeline.common import get_data_bucket, get_s3_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DATASET_ID = "ziya07/smart-logistics-supply-chain-dataset"
S3_RAW_PREFIX = "raw"
RAW_DATA_FILENAME = "logistics.csv"


def download_dataset() -> Path:
    """Download dataset from Kaggle using kagglehub.

    Returns:
        Path to the downloaded dataset directory.
    """
    logger.info(f"Downloading dataset: {DATASET_ID}")
    dataset_path = kagglehub.dataset_download(DATASET_ID)
    logger.info(f"Dataset downloaded to: {dataset_path}")
    return Path(dataset_path)


def find_csv_file(source_dir: Path) -> Path:
    """Find the main CSV file in the downloaded directory.

    Args:
        source_dir: Path to the kagglehub download directory.

    Returns:
        Path to the CSV file.
    """
    csv_files = list(source_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {source_dir}")

    # Use the first CSV file (or the one that matches expected name)
    source_file = csv_files[0]
    for f in csv_files:
        if "logistics" in f.name.lower() or "supply" in f.name.lower():
            source_file = f
            break

    logger.info(f"Found CSV file: {source_file}")
    return source_file


def upload_to_s3(local_path: Path) -> str:
    """Upload data file directly to S3 bucket.

    Args:
        local_path: Path to the local file to upload.

    Returns:
        S3 URI of the uploaded file.
    """
    s3_client = get_s3_client()
    bucket = get_data_bucket()
    s3_key = f"{S3_RAW_PREFIX}/{RAW_DATA_FILENAME}"

    logger.info(f"Uploading {local_path} to s3://{bucket}/{s3_key}")
    s3_client.upload_file(str(local_path), bucket, s3_key)

    s3_uri = f"s3://{bucket}/{s3_key}"
    logger.info(f"Upload complete: {s3_uri}")
    return s3_uri


def run_ingestion() -> dict:
    """Run the full data ingestion pipeline.

    Downloads from Kaggle and uploads directly to S3 (no local storage).

    Returns:
        Dictionary with ingestion results.
    """
    logger.info("=" * 50)
    logger.info("Starting Data Ingestion Pipeline")
    logger.info("=" * 50)

    # Step 1: Download from Kaggle (to kagglehub cache)
    download_path = download_dataset()

    # Step 2: Find the CSV file
    csv_file = find_csv_file(download_path)

    # Step 3: Upload directly to S3
    s3_uri = upload_to_s3(csv_file)

    result = {
        "s3_uri": s3_uri,
        "status": "success",
    }

    logger.info("=" * 50)
    logger.info("Data Ingestion Complete!")
    logger.info(f"  S3: {s3_uri}")
    logger.info("=" * 50)

    return result


if __name__ == "__main__":
    run_ingestion()
