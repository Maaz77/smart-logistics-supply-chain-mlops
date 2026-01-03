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
    """Upload local files to S3 (only if missing or newer/different)."""
    s3 = get_s3_client()

    if not local_dir.exists():
        return

    # Get existing S3 objects to check what's already there
    # Store by the relative path (without prefix) for comparison
    s3_objects = {}
    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                s3_key = obj["Key"]
                # Convert to relative path (remove prefix if present, normalize)
                if prefix and s3_key.startswith(prefix):
                    relative_key = s3_key[len(prefix):].lstrip("/")
                else:
                    relative_key = s3_key
                # Normalize path separators
                relative_key = relative_key.replace("\\", "/")
                s3_objects[relative_key] = {
                    "key": s3_key,
                    "last_modified": obj["LastModified"],
                    "size": obj["Size"]
                }
    except ClientError:
        pass  # Bucket might be empty or not exist

    uploaded = 0
    skipped = 0

    for file_path in local_dir.rglob("*"):
        if file_path.is_file():
            # Skip gitkeep and DS_Store
            if file_path.name in [".gitkeep", ".DS_Store"]:
                continue

            # Get relative path and normalize
            relative_path = file_path.relative_to(local_dir)
            relative_key = relative_path.as_posix()  # Use forward slashes

            # Build S3 key
            if prefix:
                s3_key = f"{prefix}/{relative_key}".replace("//", "/")
            else:
                s3_key = relative_key

            # Check if file needs to be uploaded
            should_upload = True
            if relative_key in s3_objects:
                s3_obj = s3_objects[relative_key]
                local_mtime = file_path.stat().st_mtime
                s3_mtime = s3_obj["last_modified"].timestamp()
                local_size = file_path.stat().st_size
                s3_size = s3_obj["size"]

                # Only skip if local is older/equal AND sizes match
                if local_mtime <= s3_mtime and local_size == s3_size:
                    should_upload = False

            if should_upload:
                try:
                    s3.upload_file(str(file_path), bucket, s3_key)
                    print(f"  upload: {file_path} -> s3://{bucket}/{s3_key}")
                    uploaded += 1
                except ClientError as e:
                    print(f"  error uploading {file_path}: {e}", file=sys.stderr)
            else:
                skipped += 1

    if skipped > 0:
        print(f"  skipped: {skipped} file(s) already up-to-date in S3")
    if uploaded > 0:
        print(f"  uploaded: {uploaded} file(s) to S3")


def sync_s3_to_local(bucket: str, local_dir: Path, prefix: str = ""):
    """Download S3 files to local directory (only if missing or newer/different)."""
    s3 = get_s3_client()

    local_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0

    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in pages:
            for obj in page.get("Contents", []):
                s3_key = obj["Key"]

                # Calculate local path - normalize path separators
                if prefix and s3_key.startswith(prefix):
                    relative_key = s3_key[len(prefix):].lstrip("/")
                else:
                    relative_key = s3_key
                relative_key = relative_key.replace("\\", "/")

                local_path = local_dir / relative_key

                # Skip gitkeep and DS_Store
                if local_path.name in [".gitkeep", ".DS_Store"]:
                    continue

                # Check if file needs to be downloaded
                should_download = True
                if local_path.exists():
                    local_mtime = local_path.stat().st_mtime
                    s3_mtime = obj["LastModified"].timestamp()
                    local_size = local_path.stat().st_size
                    s3_size = obj["Size"]

                    # Only skip if S3 is older/equal AND sizes match
                    if s3_mtime <= local_mtime and s3_size == local_size:
                        should_download = False

                if should_download:
                    # Create parent directories
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        s3.download_file(bucket, s3_key, str(local_path))
                        print(f"  download: s3://{bucket}/{s3_key} -> {local_path}")
                        downloaded += 1
                    except ClientError as e:
                        print(f"  error downloading {s3_key}: {e}", file=sys.stderr)
                else:
                    skipped += 1

        if skipped > 0:
            print(f"  skipped: {skipped} file(s) already up-to-date locally")
        if downloaded > 0:
            print(f"  downloaded: {downloaded} file(s) from S3")

    except ClientError as e:
        if "NoSuchBucket" in str(e):
            print(f"  bucket {bucket} does not exist, skipping")
        else:
            print(f"  error listing {bucket}: {e}", file=sys.stderr)


def main():
    """Run bidirectional sync."""
    # Script is at infra_aws/scripts/s3_sync.py, so go up 3 levels to project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent
    data_dir = project_root / "data"
    models_dir = project_root / "models"

    # Verify paths are correct
    if not project_root.exists():
        print(f"Error: Project root not found at {project_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Project root: {project_root}")
    print(f"Data directory: {data_dir}")
    print(f"Models directory: {models_dir}")
    print()

    print("🔄 Syncing local folders to S3 (LocalStack)...")
    sync_local_to_s3(data_dir, "smart-logistics-data")
    sync_local_to_s3(models_dir, "mlflow-model-registry")

    print("🔄 Syncing S3 to local folders...")
    sync_s3_to_local("smart-logistics-data", data_dir)
    sync_s3_to_local("mlflow-model-registry", models_dir)

    print("✓ Sync complete")


if __name__ == "__main__":
    main()
