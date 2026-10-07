#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Execute Athena DDL to create Conversational Analytics tables.

Reads DDL from schemas/athena_ddl.sql, replaces S3 bucket placeholder,
executes each statement in Athena, and runs MSCK REPAIR TABLE for
partitioned tables.

Prerequisites:
1. CDK stack deployed (creates S3 buckets and Athena workgroup)
2. Data uploaded to S3 (run upload_to_s3.py first)

Usage:
    uv run python scripts/create_tables.py

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import os
import re
import sys
import time
from pathlib import Path

import boto3

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conversational_analytics.env import load_env
from conversational_analytics.schema_definitions import TABLE_PARTITIONS, TABLES

# Same .env precedence as the CDK app (see conversational_analytics.env)
load_env()


def get_config() -> dict:
    """Get configuration from environment."""
    region = os.getenv("AWS_REGION", "eu-west-1")
    account_id = os.getenv("AWS_ACCOUNT_ID", "")
    bucket_prefix = os.getenv("S3_BUCKET_PREFIX", "conversational-analytics")
    workgroup = os.getenv("ATHENA_WORKGROUP", "conversational-analytics-workgroup")

    if not account_id:
        raise ValueError(
            "AWS_ACCOUNT_ID environment variable is required. "
            "Please set it in your .env file."
        )

    data_bucket = f"{bucket_prefix}-{account_id}-{region}"

    return {
        "region": region,
        "data_bucket": data_bucket,
        "workgroup": workgroup,
        "database": "conversational_analytics",
    }


def get_athena_client(region: str):
    """Create Athena client."""
    return boto3.client("athena", region_name=region)


def read_ddl_file() -> str:
    """Read DDL file contents."""
    ddl_path = Path(__file__).parent.parent / "schemas" / "athena_ddl.sql"
    if not ddl_path.exists():
        raise FileNotFoundError(f"DDL file not found: {ddl_path}")
    return ddl_path.read_text()


def parse_ddl_statements(ddl_content: str, bucket: str) -> list[str]:
    """Parse DDL content into individual statements.

    Args:
        ddl_content: Raw DDL file contents
        bucket: S3 bucket name to substitute

    Returns:
        List of SQL statements ready for execution
    """
    # Replace bucket placeholder
    ddl_content = ddl_content.replace("${S3_BUCKET}", bucket)

    # Split into statements (on semicolon followed by newline or end)
    # Ignore comments and empty lines
    statements = []
    current_stmt = []

    for line in ddl_content.split("\n"):
        stripped = line.strip()

        # Skip empty lines and full-line comments
        if not stripped or stripped.startswith("--"):
            continue

        current_stmt.append(line)

        # Check if statement ends
        if stripped.endswith(";"):
            stmt = "\n".join(current_stmt).strip()
            if stmt:
                statements.append(stmt)
            current_stmt = []

    return statements


def wait_for_query(athena_client, execution_id: str, timeout: int = 120) -> dict:
    """Wait for Athena query to complete.

    Args:
        athena_client: boto3 Athena client
        execution_id: Query execution ID
        timeout: Maximum wait time in seconds

    Returns:
        Query execution response

    Raises:
        RuntimeError: If query fails
        TimeoutError: If query exceeds timeout
    """
    start = time.time()
    poll_interval = 0.5

    while time.time() - start < timeout:
        response = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = response["QueryExecution"]["Status"]["State"]

        if state == "SUCCEEDED":
            return response
        elif state in ("FAILED", "CANCELLED"):
            reason = response["QueryExecution"]["Status"].get(
                "StateChangeReason", "Unknown error"
            )
            raise RuntimeError(f"Query {state}: {reason}")

        time.sleep(poll_interval)
        # Increase poll interval up to 2 seconds
        poll_interval = min(poll_interval * 1.5, 2.0)

    raise TimeoutError(f"Query did not complete within {timeout}s")


def execute_statement(athena_client, statement: str, config: dict) -> dict:
    """Execute a single DDL statement in Athena.

    Args:
        athena_client: boto3 Athena client
        statement: SQL statement to execute
        config: Configuration dictionary

    Returns:
        Query execution response
    """
    response = athena_client.start_query_execution(
        QueryString=statement,
        QueryExecutionContext={"Database": config["database"]},
        WorkGroup=config["workgroup"],
    )
    execution_id = response["QueryExecutionId"]

    return wait_for_query(athena_client, execution_id)


def drop_table_if_exists(athena_client, table: str, config: dict) -> bool:
    """Drop table if it exists.

    Args:
        athena_client: boto3 Athena client
        table: Table name
        config: Configuration dictionary

    Returns:
        True if dropped or didn't exist, False on error
    """
    try:
        statement = f"DROP TABLE IF EXISTS {config['database']}.{table}"
        execute_statement(athena_client, statement, config)
        return True
    except Exception as e:
        print(f"    Warning: Could not drop table {table}: {e}")
        return True  # Continue anyway


def run_msck_repair(athena_client, table: str, config: dict) -> bool:
    """Run MSCK REPAIR TABLE to discover partitions.

    Args:
        athena_client: boto3 Athena client
        table: Table name
        config: Configuration dictionary

    Returns:
        True if successful
    """
    statement = f"MSCK REPAIR TABLE {config['database']}.{table}"
    try:
        execute_statement(athena_client, statement, config)
        return True
    except Exception as e:
        print(f"    Warning: MSCK REPAIR failed for {table}: {e}")
        return False


def extract_table_name(statement: str) -> str | None:
    """Extract table name from CREATE TABLE statement."""
    match = re.search(
        r"CREATE\s+EXTERNAL\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+\.)?(\w+)",
        statement,
        re.IGNORECASE,
    )
    if match:
        return match.group(2)
    return None


def main():
    start_time = time.time()
    print("=" * 60)
    print("Athena Table Creation")
    print("=" * 60)

    # Get configuration
    try:
        config = get_config()
    except ValueError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    print(f"\nRegion:     {config['region']}")
    print(f"Workgroup:  {config['workgroup']}")
    print(f"Database:   {config['database']}")
    print(f"Data:       s3://{config['data_bucket']}/")
    print("Results:    set by the workgroup (aws-athena-query-results-analytics-<account>-<region>)")

    # Read DDL file
    print("\nReading DDL file...")
    try:
        ddl_content = read_ddl_file()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Parse statements
    statements = parse_ddl_statements(ddl_content, config["data_bucket"])
    print(f"  Found {len(statements)} DDL statements")

    # Create Athena client
    athena_client = get_athena_client(config["region"])

    # Execute each statement
    print("\n" + "-" * 60)
    print("Executing DDL Statements")
    print("-" * 60)

    success_count = 0
    error_count = 0
    created_tables = []

    for i, statement in enumerate(statements, 1):
        table_name = extract_table_name(statement)
        label = table_name or f"Statement {i}"

        print(f"\n[{i}/{len(statements)}] Creating {label}...")

        # Drop existing table first (for clean recreation)
        if table_name:
            print("    Dropping existing table if present...")
            drop_table_if_exists(athena_client, table_name, config)

        # Execute CREATE statement
        try:
            execute_statement(athena_client, statement, config)
            print("    Created successfully")
            success_count += 1

            if table_name:
                created_tables.append(table_name)
        except Exception as e:
            print(f"    ERROR: {e}")
            error_count += 1

    # Run MSCK REPAIR for partitioned tables
    print("\n" + "-" * 60)
    print("Discovering Partitions (MSCK REPAIR)")
    print("-" * 60)

    partitioned_tables = [t for t in TABLES if TABLE_PARTITIONS.get(t)]
    repair_success = 0
    repair_errors = 0

    for table in partitioned_tables:
        if table not in created_tables:
            print(f"\n  Skipping {table} (not created)")
            continue

        print(f"\n  Repairing {table}...")
        partitions = TABLE_PARTITIONS.get(table, [])
        print(f"    Partitions: {', '.join(partitions)}")

        if run_msck_repair(athena_client, table, config):
            print("    Partitions discovered successfully")
            repair_success += 1
        else:
            repair_errors += 1

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("Table Creation Complete!")
    print("=" * 60)
    print(f"\nDDL Statements:  {success_count} succeeded, {error_count} failed")
    print(f"MSCK Repairs:    {repair_success} succeeded, {repair_errors} failed")
    print(f"Time:            {elapsed:.1f}s")

    if error_count > 0 or repair_errors > 0:
        print("\n[WARNING] Some operations failed. Check errors above.")
        print("\nNext step: Verify tables with 'uv run python scripts/validate_tables.py'")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All tables created successfully!")
        print("\nCreated tables:")
        for table in created_tables:
            partitions = TABLE_PARTITIONS.get(table, [])
            partition_info = f" (partitioned by: {', '.join(partitions)})" if partitions else ""
            print(f"  - {config['database']}.{table}{partition_info}")

        print("\nNext steps:")
        print("  1. Validate tables: uv run python scripts/validate_tables.py")
        print("  2. Deploy QuickSight: uv run cdk deploy ConversationalAnalytics-QuickSight ConversationalAnalytics-QuickSight-Topics")

    return 0


if __name__ == "__main__":
    sys.exit(main())
