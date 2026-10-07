#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Upload generated Parquet files to S3 data lake bucket.

Uploads data from data/ directory to S3, preserving partition structure.
Must be run after generate_data.py and after CDK stack deployment.

Usage:
    uv run python scripts/upload_to_s3.py

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import os
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conversational_analytics.env import load_env
from conversational_analytics.generators import get_data_dir
from conversational_analytics.schema_definitions import TABLES

# Same .env precedence as the CDK app (see conversational_analytics.env)
load_env()


def get_bucket_name() -> str:
    """Get S3 bucket name from environment configuration."""
    region = os.getenv("AWS_REGION", "eu-west-1")
    account_id = os.getenv("AWS_ACCOUNT_ID", "")
    bucket_prefix = os.getenv("S3_BUCKET_PREFIX", "conversational-analytics")

    if not account_id:
        raise ValueError(
            "AWS_ACCOUNT_ID environment variable is required. "
            "Please set it in your .env file."
        )

    return f"{bucket_prefix}-{account_id}-{region}"


def get_s3_client():
    """Create S3 client."""
    region = os.getenv("AWS_REGION", "eu-west-1")
    return boto3.client("s3", region_name=region)


def upload_file(s3_client, bucket: str, local_path: Path, s3_key: str) -> bool:
    """Upload a single file to S3.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        local_path: Local file path
        s3_key: S3 object key

    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client.upload_file(
            str(local_path),
            bucket,
            s3_key,
            ExtraArgs={
                "ContentType": "application/x-parquet",
            },
        )
        return True
    except ClientError as e:
        print(f"  ERROR uploading {local_path}: {e}")
        return False


def upload_table(s3_client, bucket: str, table_name: str, data_dir: Path) -> dict:
    """Upload all files for a table to S3.

    Preserves partition structure (e.g., country=ES/year=2025/month=01/).

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        table_name: Name of the table
        data_dir: Base data directory

    Returns:
        Dictionary with upload statistics
    """
    table_dir = data_dir / table_name
    if not table_dir.exists():
        return {"files": 0, "errors": 1, "bytes": 0, "message": "Directory not found"}

    stats = {"files": 0, "errors": 0, "bytes": 0}

    # Find all Parquet files (including in partition directories)
    parquet_files = list(table_dir.rglob("*.parquet"))

    if not parquet_files:
        return {"files": 0, "errors": 1, "bytes": 0, "message": "No Parquet files found"}

    for local_file in parquet_files:
        # Calculate S3 key preserving partition structure
        relative_path = local_file.relative_to(data_dir)
        s3_key = str(relative_path)

        # Upload file
        file_size = local_file.stat().st_size
        if upload_file(s3_client, bucket, local_file, s3_key):
            stats["files"] += 1
            stats["bytes"] += file_size
        else:
            stats["errors"] += 1

    return stats


def verify_bucket_exists(s3_client, bucket: str) -> bool:
    """Verify that the S3 bucket exists."""
    try:
        s3_client.head_bucket(Bucket=bucket)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            return False
        elif error_code == "403":
            print(f"ERROR: Access denied to bucket {bucket}")
            return False
        else:
            raise


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main():
    start_time = time.time()
    print("=" * 60)
    print("S3 Upload")
    print("=" * 60)

    # Get configuration
    try:
        bucket = get_bucket_name()
    except ValueError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    data_dir = get_data_dir()

    print(f"\nSource:      {data_dir}")
    print(f"Destination: s3://{bucket}/")

    # Verify data directory exists
    if not data_dir.exists():
        print(f"\nERROR: Data directory not found: {data_dir}")
        print("Run 'uv run python scripts/generate_data.py' first.")
        sys.exit(1)

    # Create S3 client
    s3_client = get_s3_client()

    # Verify bucket exists
    print("\nVerifying bucket...")
    if not verify_bucket_exists(s3_client, bucket):
        print(f"\nERROR: Bucket does not exist: {bucket}")
        print("Deploy the CDK stack first: uv run cdk deploy")
        sys.exit(1)

    print(f"  Bucket {bucket} exists [OK]")

    # Upload each table
    print("\n" + "-" * 60)
    print("Uploading Tables")
    print("-" * 60)

    total_files = 0
    total_errors = 0
    total_bytes = 0

    for table in TABLES:
        print(f"\n[{TABLES.index(table) + 1}/{len(TABLES)}] Uploading {table}...")

        stats = upload_table(s3_client, bucket, table, data_dir)

        if "message" in stats:
            print(f"  {stats['message']}")
            total_errors += stats["errors"]
        else:
            print(f"  Uploaded {stats['files']} files ({format_bytes(stats['bytes'])})")
            if stats["errors"] > 0:
                print(f"  Errors: {stats['errors']}")

            total_files += stats["files"]
            total_errors += stats["errors"]
            total_bytes += stats["bytes"]

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("Upload Complete!")
    print("=" * 60)
    print(f"\nTotal files:  {total_files:,}")
    print(f"Total size:   {format_bytes(total_bytes)}")
    print(f"Total errors: {total_errors}")
    print(f"Time:         {elapsed:.1f}s")
    print(f"\nData location: s3://{bucket}/")

    if total_errors > 0:
        print("\n[WARNING] Some files failed to upload. Check errors above.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All files uploaded successfully!")
        print("\nNext step: Run 'uv run python scripts/create_tables.py' to create Athena tables.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
