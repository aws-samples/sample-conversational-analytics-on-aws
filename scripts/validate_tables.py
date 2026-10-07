#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Validate Athena table setup and row counts.

Connects to Athena and verifies:
1. All 6 tables exist in conversational_analytics database
2. Row counts match target volumes from schema_definitions

Usage:
    uv run python scripts/validate_tables.py

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import os
import sys
import time
from pathlib import Path

import boto3

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conversational_analytics.env import load_env
from conversational_analytics.schema_definitions import TABLE_ROW_COUNTS, TABLES

# Same .env precedence as the CDK app (see conversational_analytics.env)
load_env()


def get_config():
    """Load configuration from environment."""
    region = os.getenv("AWS_REGION", "eu-west-1")
    workgroup = os.getenv("ATHENA_WORKGROUP", "conversational-analytics-workgroup")

    return {
        "region": region,
        "workgroup": workgroup,
        "database": "conversational_analytics",
    }


def wait_for_query(athena_client, execution_id: str, timeout: int = 60) -> dict:
    """Wait for Athena query to complete."""
    start = time.time()
    while time.time() - start < timeout:
        response = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = response["QueryExecution"]["Status"]["State"]

        if state == "SUCCEEDED":
            return response
        elif state in ("FAILED", "CANCELLED"):
            reason = response["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
            raise RuntimeError(f"Query {state}: {reason}")

        time.sleep(1)

    raise TimeoutError(f"Query did not complete within {timeout}s")


def run_query(athena_client, query: str, config: dict) -> list[dict]:
    """Execute Athena query and return results."""
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": config["database"]},
        WorkGroup=config["workgroup"],
    )
    execution_id = response["QueryExecutionId"]

    wait_for_query(athena_client, execution_id)

    # Get results
    results = []
    header = None
    paginator = athena_client.get_paginator("get_query_results")
    for page in paginator.paginate(QueryExecutionId=execution_id):
        rows = page["ResultSet"]["Rows"]
        if header is None and rows:  # First page includes header
            header = [col.get("VarCharValue", "") for col in rows[0]["Data"]]
            rows = rows[1:]

        for row in rows:
            values = [col.get("VarCharValue", "") for col in row["Data"]]
            if header:
                results.append(dict(zip(header, values)))

    return results


def check_table_exists(athena_client, table: str, config: dict) -> bool:
    """Check if table exists in database."""
    query = f"SHOW TABLES IN {config['database']} '{table}'"
    try:
        # SHOW TABLES doesn't return header rows, so use raw result check
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": config["database"]},
            WorkGroup=config["workgroup"],
        )
        execution_id = response["QueryExecutionId"]
        wait_for_query(athena_client, execution_id)

        result = athena_client.get_query_results(QueryExecutionId=execution_id)
        rows = result["ResultSet"]["Rows"]
        return len(rows) > 0
    except Exception as e:
        print(f"    Error checking {table}: {e}")
        return False


def get_row_count(athena_client, table: str, config: dict) -> int:
    """Get row count for table."""
    query = f"SELECT COUNT(*) as cnt FROM {config['database']}.{table}"  # nosec B608 - identifiers and dates come from code constants and the deployer's own config, not user input
    results = run_query(athena_client, query, config)
    return int(results[0]["cnt"]) if results else 0


def main():
    config = get_config()
    print("=" * 60)
    print("Table Validation")
    print("=" * 60)
    print(f"\nRegion:    {config['region']}")
    print(f"Workgroup: {config['workgroup']}")
    print(f"Database:  {config['database']}")
    print("Output:    set by the workgroup (aws-athena-query-results-analytics-<account>-<region>)")

    athena_client = boto3.client("athena", region_name=config["region"])

    print("\n" + "-" * 60)
    print("Table Existence Check")
    print("-" * 60)

    all_exist = True
    for table in TABLES:
        exists = check_table_exists(athena_client, table, config)
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {table:20} {status}")
        if not exists:
            all_exist = False

    if not all_exist:
        print("\n[ERROR] Some tables are missing. Run create_tables.py first.")
        sys.exit(1)

    print("\n" + "-" * 60)
    print("Row Count Validation")
    print("-" * 60)
    print(f"  {'Table':20} {'Actual':>12} {'Target':>12} {'Status':>10}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*10}")

    all_valid = True
    tolerance = 0.05  # 5% tolerance

    for table in TABLES:
        try:
            actual = get_row_count(athena_client, table, config)
            target = TABLE_ROW_COUNTS.get(table, 0)

            if target > 0:
                diff = abs(actual - target) / target
                if diff <= tolerance:
                    status = "[OK]"
                elif actual > 0:
                    status = "[WARN]"
                else:
                    status = "[EMPTY]"
                    all_valid = False
            else:
                status = "[N/A]"

            print(f"  {table:20} {actual:>12,} {target:>12,} {status:>10}")
        except Exception as e:
            print(f"  {table:20} {'ERROR':>12} {TABLE_ROW_COUNTS.get(table, 0):>12,} [FAIL]")
            print(f"    Error: {e}")
            all_valid = False

    print("\n" + "=" * 60)
    if all_valid:
        print("[SUCCESS] All tables validated successfully!")
    else:
        print("[WARNING] Some tables have issues. Check output above.")
    print("=" * 60)

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
