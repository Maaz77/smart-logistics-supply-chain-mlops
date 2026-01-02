#!/usr/bin/env python3
"""
S3 Sync Script for Smart Logistics.

Syncs local data/ and models/ folders with S3 buckets on LocalStack.
Replaces awslocal s3 sync since awscli was removed due to dependency conflicts.
"""

import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def get_s3_client():
    """Get S3 client configured for LocalStack."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


def sync_local_to_s3(local_dir: Path, bucket: str, prefix: str = ""):
    """Upload local files to S3."""
    s3 = get_s3_client()

    if not local_dir.exists():
        return

    for file_path in local_dir.rglob("*"):
        if file_path.is_file():
            # Skip gitkeep and DS_Store
            if file_path.name in [".gitkeep", ".DS_Store"]:
                continue

            relative_path = file_path.relative_to(local_dir)
            s3_key = f"{prefix}/{relative_path}" if prefix else str(relative_path)
            s3_key = s3_key.replace("\\", "/")  # Windows compatibility

            try:
                s3.upload_file(str(file_path), bucket, s3_key)
                print(f"  upload: {file_path} -> s3://{bucket}/{s3_key}")
            except ClientError as e:
                print(f"  error uploading {file_path}: {e}", file=sys.stderr)


def sync_s3_to_local(bucket: str, local_dir: Path, prefix: str = ""):
    """Download S3 files to local directory."""
    s3 = get_s3_client()

    local_dir.mkdir(parents=True, exist_ok=True)

    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in pages:
            for obj in page.get("Contents", []):
                s3_key = obj["Key"]

                # Calculate local path
                if prefix:
                    relative_key = s3_key[len(prefix):].lstrip("/")
                else:
                    relative_key = s3_key

                local_path = local_dir / relative_key

                # Create parent directories
                local_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    s3.download_file(bucket, s3_key, str(local_path))
                    print(f"  download: s3://{bucket}/{s3_key} -> {local_path}")
                except ClientError as e:
                    print(f"  error downloading {s3_key}: {e}", file=sys.stderr)
    except ClientError as e:
        if "NoSuchBucket" in str(e):
            print(f"  bucket {bucket} does not exist, skipping")
        else:
            print(f"  error listing {bucket}: {e}", file=sys.stderr)


def main():
    """Run bidirectional sync."""
    # scripts/ is directly under project root
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    models_dir = project_root / "models"

    print("🔄 Syncing local folders to S3 (LocalStack)...")
    sync_local_to_s3(data_dir, "smart-logistics-data")
    sync_local_to_s3(models_dir, "mlflow-model-registry")

    print("🔄 Syncing S3 to local folders...")
    sync_s3_to_local("smart-logistics-data", data_dir)
    sync_s3_to_local("mlflow-model-registry", models_dir)

    print("✓ Sync complete")


if __name__ == "__main__":
    main()
