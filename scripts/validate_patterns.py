#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Validate UC-2 Chargeback Spike Pattern in Athena.

Verifies the embedded pattern for "Why did chargebacks increase last week?":
1. Spike detection: ~3.5x increase during week of 2026-01-15
2. Root cause: FastShop Online merchant (~80% of spike)
3. Type breakdown: 85% unauthorized chargebacks
4. Reason code: 65% fraud_card_not_present

Usage:
    uv run python scripts/validate_patterns.py

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
from conversational_analytics.patterns.chargeback_spike import (
    BASELINE_DAILY_CHARGEBACKS,
    FASTSHOP_MERCHANT,
    SPIKE_END_DATE,
    SPIKE_MULTIPLIER,
    SPIKE_START_DATE,
    SPIKE_TYPE_DISTRIBUTION,
    SPIKE_UNAUTHORIZED_REASONS,
)
from conversational_analytics.schema_definitions import ChargebackReasonCode

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


def wait_for_query(athena_client, execution_id: str, timeout: int = 120) -> dict:
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

        time.sleep(2)

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

    results = []
    paginator = athena_client.get_paginator("get_query_results")
    for page in paginator.paginate(QueryExecutionId=execution_id):
        rows = page["ResultSet"]["Rows"]
        if not results:
            header = [col["VarCharValue"] for col in rows[0]["Data"]]
            rows = rows[1:]

        for row in rows:
            values = [col.get("VarCharValue", "") for col in row["Data"]]
            results.append(dict(zip(header, values)))

    return results


def validate_weekly_spike(athena_client, config: dict) -> dict:
    """Query 1: Compare the spike window with the average week before it.

    Uses the exact spike window rather than calendar weeks, which would split the
    spike across two weeks and count part of it as baseline.
    """
    print("\n[Query 1] Spike window vs. baseline weekly chargeback counts...")

    query = f"""
    SELECT
        SUM(CASE WHEN chargeback_date BETWEEN DATE '{SPIKE_START_DATE}' AND DATE '{SPIKE_END_DATE}'
                 THEN 1 ELSE 0 END) AS spike_count,
        SUM(CASE WHEN chargeback_date < DATE '{SPIKE_START_DATE}' THEN 1 ELSE 0 END) AS baseline_count,
        date_diff('day', MIN(chargeback_date), DATE '{SPIKE_START_DATE}') AS baseline_days
    FROM conversational_analytics.chargebacks
    """  # nosec B608 - built from code constants, not user input

    results = run_query(athena_client, query, config)
    row = results[0] if results else {}
    spike_count = int(row.get("spike_count") or 0)
    baseline_days = int(row.get("baseline_days") or 0)
    baseline_count = int(row.get("baseline_count") or 0)

    avg_baseline = baseline_count / baseline_days * 7 if baseline_days else BASELINE_DAILY_CHARGEBACKS * 7

    return {
        "spike_week": {"week": str(SPIKE_START_DATE), "count": spike_count},
        "avg_baseline": avg_baseline,
        "multiplier": spike_count / avg_baseline if avg_baseline else 0,
    }


def validate_merchant_concentration(athena_client, config: dict) -> dict:
    """Query 2: Top merchants during spike week."""
    print("\n[Query 2] Top merchants during spike week...")

    query = f"""
    SELECT
        m.merchant_name,
        c.merchant_id,
        COUNT(*) as cb_count,
        CAST(COUNT(*) AS DOUBLE) / SUM(COUNT(*)) OVER () * 100 as pct
    FROM conversational_analytics.chargebacks c
    JOIN conversational_analytics.merchants m ON c.merchant_id = m.merchant_id
    WHERE c.chargeback_date >= DATE '{SPIKE_START_DATE}'
      AND c.chargeback_date <= DATE '{SPIKE_END_DATE}'
    GROUP BY m.merchant_name, c.merchant_id
    ORDER BY cb_count DESC
    LIMIT 5
    """  # nosec B608 - built from code constants, not user input

    results = run_query(athena_client, query, config)

    fastshop_pct = 0.0
    for row in results:
        if FASTSHOP_MERCHANT.merchant_name in row["merchant_name"]:
            fastshop_pct = float(row["pct"])
            break

    return {
        "top_merchants": results,
        "fastshop_pct": fastshop_pct,
    }


def validate_unauthorized_rate(athena_client, config: dict) -> dict:
    """Query 3: Unauthorized percentage during spike."""
    print("\n[Query 3] Chargeback type distribution during spike...")

    query = f"""
    SELECT
        chargeback_type,
        COUNT(*) as cb_count,
        CAST(COUNT(*) AS DOUBLE) / SUM(COUNT(*)) OVER () * 100 as pct
    FROM conversational_analytics.chargebacks
    WHERE chargeback_date >= DATE '{SPIKE_START_DATE}'
      AND chargeback_date <= DATE '{SPIKE_END_DATE}'
    GROUP BY chargeback_type
    ORDER BY cb_count DESC
    """  # nosec B608 - built from code constants, not user input

    results = run_query(athena_client, query, config)

    unauthorized_pct = 0.0
    for row in results:
        if row["chargeback_type"] == "unauthorized":
            unauthorized_pct = float(row["pct"])
            break

    return {
        "type_breakdown": results,
        "unauthorized_pct": unauthorized_pct,
    }


def validate_cnp_fraud_rate(athena_client, config: dict) -> dict:
    """Query 4: fraud_card_not_present percentage of unauthorized."""
    print("\n[Query 4] Reason code distribution for unauthorized chargebacks...")

    query = f"""
    SELECT
        reason_code,
        COUNT(*) as cb_count,
        CAST(COUNT(*) AS DOUBLE) / SUM(COUNT(*)) OVER () * 100 as pct
    FROM conversational_analytics.chargebacks
    WHERE chargeback_date >= DATE '{SPIKE_START_DATE}'
      AND chargeback_date <= DATE '{SPIKE_END_DATE}'
      AND chargeback_type = 'unauthorized'
    GROUP BY reason_code
    ORDER BY cb_count DESC
    """  # nosec B608 - built from code constants, not user input

    results = run_query(athena_client, query, config)

    cnp_pct = 0.0
    for row in results:
        if row["reason_code"] == ChargebackReasonCode.FRAUD_CARD_NOT_PRESENT.value:
            cnp_pct = float(row["pct"])
            break

    return {
        "reason_breakdown": results,
        "cnp_fraud_pct": cnp_pct,
    }


def main():
    config = get_config()

    print("=" * 70)
    print("UC-2 Chargeback Root Cause Pattern Validation")
    print("=" * 70)
    print(f"\nRegion:      {config['region']}")
    print(f"Workgroup:   {config['workgroup']}")
    print(f"Database:    {config['database']}")
    print(f"\nSpike Period: {SPIKE_START_DATE} to {SPIKE_END_DATE}")
    print(f"Target Merchant: {FASTSHOP_MERCHANT.merchant_name}")

    athena_client = boto3.client("athena", region_name=config["region"])

    # Run validations
    results = {}

    try:
        results["weekly"] = validate_weekly_spike(athena_client, config)
        results["merchants"] = validate_merchant_concentration(athena_client, config)
        results["unauthorized"] = validate_unauthorized_rate(athena_client, config)
        results["cnp_fraud"] = validate_cnp_fraud_rate(athena_client, config)
    except Exception as e:
        print(f"\n[ERROR] Query failed: {e}")
        return 1

    # Print results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    # Weekly spike
    weekly = results["weekly"]
    if weekly["spike_week"]:
        spike_count = weekly["spike_week"]["count"]
        multiplier = weekly["multiplier"]
        print(f"\n[1] Week of 2026-01-15: {spike_count:,} chargebacks")
        print(f"    Baseline average:   {weekly['avg_baseline']:.0f} chargebacks/week")
        print(f"    Spike multiplier:   {multiplier:.1f}x")
        target_mult = SPIKE_MULTIPLIER
        status = "[PASS]" if multiplier >= target_mult * 0.8 else "[WARN]"
        print(f"    Target: ~{target_mult}x spike {status}")
    else:
        print("\n[1] [FAIL] Could not identify spike week")

    # Merchant concentration
    merchants = results["merchants"]
    print(f"\n[2] FastShop Online share: {merchants['fastshop_pct']:.1f}%")
    print("    Top 5 merchants during spike:")
    for row in merchants["top_merchants"][:5]:
        print(f"      - {row['merchant_name']}: {float(row['pct']):.1f}%")
    status = "[PASS]" if merchants["fastshop_pct"] >= 75 else "[WARN]"
    print(f"    Target: >75% FastShop {status}")

    # Unauthorized rate
    unauthorized = results["unauthorized"]
    print(f"\n[3] Unauthorized chargebacks: {unauthorized['unauthorized_pct']:.1f}%")
    print("    Type breakdown:")
    for row in unauthorized["type_breakdown"]:
        print(f"      - {row['chargeback_type']}: {float(row['pct']):.1f}%")
    target_pct = SPIKE_TYPE_DISTRIBUTION.unauthorized * 100
    status = "[PASS]" if unauthorized["unauthorized_pct"] >= target_pct * 0.9 else "[WARN]"
    print(f"    Target: ~{target_pct:.0f}% unauthorized {status}")

    # CNP fraud rate
    cnp = results["cnp_fraud"]
    print(f"\n[4] fraud_card_not_present: {cnp['cnp_fraud_pct']:.1f}% of unauthorized")
    print("    Reason code breakdown:")
    for row in cnp["reason_breakdown"][:5]:
        print(f"      - {row['reason_code']}: {float(row['pct']):.1f}%")
    target_pct = SPIKE_UNAUTHORIZED_REASONS[ChargebackReasonCode.FRAUD_CARD_NOT_PRESENT] * 100
    status = "[PASS]" if cnp["cnp_fraud_pct"] >= target_pct * 0.9 else "[WARN]"
    print(f"    Target: ~{target_pct:.0f}% CNP fraud {status}")

    # Summary
    print("\n" + "=" * 70)
    print("EXPECTED OUTPUT SUMMARY")
    print("=" * 70)
    print(f"""
Week of 2026-01-15: ~{weekly['spike_week']['count'] if weekly['spike_week'] else 'N/A':,} chargebacks (vs ~{weekly['avg_baseline']:.0f} baseline = ~{weekly['multiplier']:.1f}x spike)
FastShop Online: {merchants['fastshop_pct']:.0f}%+ of spike week chargebacks
Unauthorized: {unauthorized['unauthorized_pct']:.0f}% of spike week chargebacks
fraud_card_not_present: {cnp['cnp_fraud_pct']:.0f}% of unauthorized chargebacks
""")

    # Overall pass/fail
    all_pass = (
        weekly["multiplier"] >= SPIKE_MULTIPLIER * 0.8
        and merchants["fastshop_pct"] >= 75
        and unauthorized["unauthorized_pct"] >= 80
        and cnp["cnp_fraud_pct"] >= 60
    )

    print("=" * 70)
    if all_pass:
        print("[SUCCESS] All UC-2 pattern validations passed!")
    else:
        print("[WARNING] Some pattern targets not met. Review results above.")
    print("=" * 70)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
