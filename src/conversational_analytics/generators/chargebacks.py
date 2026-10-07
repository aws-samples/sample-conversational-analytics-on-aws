# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Chargeback data generator with UC-2 spike pattern.

UC-2 Core Pattern:
- Spike week (2026-01-15 to 2026-01-21): ~2,500 chargebacks (10% of total)
  - 85% unauthorized, 65% fraud_card_not_present
  - FastShop Online should be >80% of spike chargebacks
- Baseline: ~22,500 chargebacks
  - 30% unauthorized, 70% authorized

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from conversational_analytics.patterns.chargeback_spike import (
    AUTHORIZED_REASONS,
    BASELINE_AMOUNT_MEAN_CENTS,
    BASELINE_AMOUNT_STD_CENTS,
    BASELINE_TYPE_DISTRIBUTION,
    BASELINE_UNAUTHORIZED_REASONS,
    DATA_END_DATE,
    DATA_START_DATE,
    FASTSHOP_MERCHANT,
    FASTSHOP_SPIKE_SHARE,
    SPIKE_AMOUNT_MAX_CENTS,
    SPIKE_AMOUNT_MEAN_CENTS,
    SPIKE_AMOUNT_MIN_CENTS,
    SPIKE_AMOUNT_STD_CENTS,
    SPIKE_END_DATE,
    SPIKE_MULTIPLIER,
    SPIKE_START_DATE,
    SPIKE_TYPE_DISTRIBUTION,
    SPIKE_UNAUTHORIZED_REASONS,
)
from conversational_analytics.schema_definitions import (
    ChargebackReasonCode,
    ChargebackStatus,
    ChargebackType,
)

from .base import generate_id, set_seed, write_parquet

# Currency by country
COUNTRY_CURRENCY = {
    "ES": "EUR",
    "DE": "EUR",
    "FR": "EUR",
    "IT": "EUR",
    "NL": "EUR",
    "PT": "EUR",
    "PL": "PLN",
    "UK": "GBP",
}


def generate_chargebacks(
    transactions_df: pd.DataFrame,
    target_count: int = 25000,
) -> pd.DataFrame:
    """Generate chargeback data with UC-2 spike pattern.

    Args:
        transactions_df: DataFrame with transaction data
        target_count: Target number of chargebacks (default 25K)
    """
    rng = set_seed(seed=45)

    # Filter to approved transactions only
    approved_txns = transactions_df[transactions_df["is_approved"]].copy()
    approved_txns["txn_date"] = pd.to_datetime(approved_txns["transaction_date"]).dt.date

    # Get FastShop transactions for spike
    # For chargebacks filed during spike week, transactions occurred 1-30 days earlier
    fastshop_txns = approved_txns[approved_txns["merchant_id"] == FASTSHOP_MERCHANT.merchant_id]
    pre_spike_start = SPIKE_START_DATE - timedelta(days=30)
    pre_spike_end = SPIKE_START_DATE - timedelta(days=1)

    # FastShop transactions that will result in chargebacks during spike week
    spike_fastshop_txns = fastshop_txns[
        (fastshop_txns["txn_date"] >= pre_spike_start) &
        (fastshop_txns["txn_date"] <= pre_spike_end)
    ]

    # Non-FastShop transactions
    non_fastshop_txns = approved_txns[approved_txns["merchant_id"] != FASTSHOP_MERCHANT.merchant_id]

    # Calculate chargeback distribution
    # For 25K target: Spike = ~10% of total, baseline = ~90%
    # Spike week should be roughly 3.5x daily rate of baseline
    spike_days = (SPIKE_END_DATE - SPIKE_START_DATE).days + 1
    total_days = (DATA_END_DATE - DATA_START_DATE).days + 1
    baseline_days = total_days - spike_days

    # Solve for spike and baseline such that:
    # spike_daily = 3.5 * baseline_daily
    # spike_days * spike_daily + baseline_days * baseline_daily = target_count
    # => spike_days * 3.5 * baseline_daily + baseline_days * baseline_daily = target
    # => baseline_daily * (spike_days * 3.5 + baseline_days) = target
    baseline_daily = target_count / (spike_days * SPIKE_MULTIPLIER + baseline_days)
    spike_daily = baseline_daily * SPIKE_MULTIPLIER

    total_spike = int(spike_days * spike_daily)
    baseline_total = target_count - total_spike

    print("Chargeback distribution plan:")
    print(f"  Spike period: {SPIKE_START_DATE} to {SPIKE_END_DATE} ({spike_days} days)")
    print(f"  Spike chargebacks: {total_spike}")
    print(f"  Baseline chargebacks: {baseline_total}")
    print(f"  Total target: {target_count}")

    records = []
    cb_idx = 1

    # ----- SPIKE PERIOD CHARGEBACKS -----
    # 80% from FastShop, 85% unauthorized, 65% fraud_card_not_present
    fastshop_spike_count = int(total_spike * FASTSHOP_SPIKE_SHARE)
    other_spike_count = total_spike - fastshop_spike_count

    print("\nGenerating spike chargebacks:")
    print(f"  FastShop: {fastshop_spike_count}")
    print(f"  Other merchants: {other_spike_count}")

    # FastShop spike chargebacks
    if len(spike_fastshop_txns) >= fastshop_spike_count:
        selected_fastshop = spike_fastshop_txns.sample(n=fastshop_spike_count, random_state=45)
    else:
        # If not enough FastShop transactions, use all and sample with replacement
        selected_fastshop = spike_fastshop_txns.sample(
            n=fastshop_spike_count,
            replace=True,
            random_state=45
        )

    # Generate spike FastShop chargebacks
    for _, txn in selected_fastshop.iterrows():
        # 85% unauthorized during spike
        is_unauthorized = rng.random() < SPIKE_TYPE_DISTRIBUTION.unauthorized

        if is_unauthorized:
            cb_type = ChargebackType.UNAUTHORIZED.value
            # Select reason from spike distribution (65% CNP)
            reasons = [r.value for r in SPIKE_UNAUTHORIZED_REASONS.keys()]
            weights = list(SPIKE_UNAUTHORIZED_REASONS.values())
            reason_code = str(rng.choice(reasons, p=np.array(weights)/sum(weights)))
        else:
            cb_type = ChargebackType.AUTHORIZED.value
            reasons = [r.value for r in AUTHORIZED_REASONS.keys()]
            weights = list(AUTHORIZED_REASONS.values())
            reason_code = str(rng.choice(reasons, p=np.array(weights)/sum(weights)))

        # Spike amounts: smaller, high-volume fraud
        amount = int(rng.normal(SPIKE_AMOUNT_MEAN_CENTS, SPIKE_AMOUNT_STD_CENTS))
        amount = max(SPIKE_AMOUNT_MIN_CENTS, min(SPIKE_AMOUNT_MAX_CENTS, amount))

        # Chargeback date: force to be within spike week
        # This ensures the spike is visible when querying by chargeback_date
        cb_date = SPIKE_START_DATE + timedelta(days=int(rng.integers(0, 7)))

        # Status: most are lost (favor cardholder in fraud cases)
        if is_unauthorized:
            status = rng.choice(
                [ChargebackStatus.LOST.value, ChargebackStatus.PENDING.value, ChargebackStatus.WON.value],
                p=[0.75, 0.15, 0.10]
            )
        else:
            status = rng.choice(
                [ChargebackStatus.LOST.value, ChargebackStatus.PENDING.value, ChargebackStatus.WON.value],
                p=[0.50, 0.20, 0.30]
            )

        # Resolution date for resolved cases
        resolution_date = None
        if status in [ChargebackStatus.LOST.value, ChargebackStatus.WON.value]:
            resolution_offset = int(rng.integers(14, 60))
            resolution_date = cb_date + timedelta(days=resolution_offset)

        currency = COUNTRY_CURRENCY.get(txn["country"], "EUR")

        records.append({
            "chargeback_id": generate_id("CB_", cb_idx, width=6),
            "transaction_id": txn["transaction_id"],
            "card_id": txn["card_id"],
            "merchant_id": txn["merchant_id"],
            "chargeback_date": cb_date,
            "chargeback_amount_cents": amount,
            "currency": currency,
            "chargeback_type": cb_type,
            "reason_code": reason_code,
            "status": status,
            "resolution_date": resolution_date,
            "year": cb_date.year,
            "month": cb_date.month,
        })
        cb_idx += 1

    # Non-FastShop spike chargebacks follow the same spike type and reason mix
    # Select transactions from before spike week that will result in chargebacks during spike
    spike_non_fastshop = non_fastshop_txns[
        (non_fastshop_txns["txn_date"] >= pre_spike_start) &
        (non_fastshop_txns["txn_date"] <= pre_spike_end)
    ]

    if len(spike_non_fastshop) >= other_spike_count:
        selected_other_spike = spike_non_fastshop.sample(n=other_spike_count, random_state=46)
    else:
        selected_other_spike = spike_non_fastshop.sample(n=other_spike_count, replace=True, random_state=46)

    for _, txn in selected_other_spike.iterrows():
        is_unauthorized = rng.random() < SPIKE_TYPE_DISTRIBUTION.unauthorized

        if is_unauthorized:
            cb_type = ChargebackType.UNAUTHORIZED.value
            reasons = [r.value for r in SPIKE_UNAUTHORIZED_REASONS.keys()]
            weights = list(SPIKE_UNAUTHORIZED_REASONS.values())
            reason_code = str(rng.choice(reasons, p=np.array(weights)/sum(weights)))
        else:
            cb_type = ChargebackType.AUTHORIZED.value
            reasons = [r.value for r in AUTHORIZED_REASONS.keys()]
            weights = list(AUTHORIZED_REASONS.values())
            reason_code = str(rng.choice(reasons, p=np.array(weights)/sum(weights)))

        amount = int(rng.normal(BASELINE_AMOUNT_MEAN_CENTS, BASELINE_AMOUNT_STD_CENTS))
        amount = max(500, min(50000, amount))

        # Force chargeback date to be within spike week
        cb_date = SPIKE_START_DATE + timedelta(days=int(rng.integers(0, 7)))

        status = rng.choice(
            [ChargebackStatus.LOST.value, ChargebackStatus.PENDING.value, ChargebackStatus.WON.value, ChargebackStatus.EXPIRED.value],
            p=[0.45, 0.20, 0.30, 0.05]
        )

        resolution_date = None
        if status in [ChargebackStatus.LOST.value, ChargebackStatus.WON.value, ChargebackStatus.EXPIRED.value]:
            resolution_offset = int(rng.integers(14, 90))
            resolution_date = cb_date + timedelta(days=resolution_offset)

        currency = COUNTRY_CURRENCY.get(txn["country"], "EUR")

        records.append({
            "chargeback_id": generate_id("CB_", cb_idx, width=6),
            "transaction_id": txn["transaction_id"],
            "card_id": txn["card_id"],
            "merchant_id": txn["merchant_id"],
            "chargeback_date": cb_date,
            "chargeback_amount_cents": amount,
            "currency": currency,
            "chargeback_type": cb_type,
            "reason_code": reason_code,
            "status": status,
            "resolution_date": resolution_date,
            "year": cb_date.year,
            "month": cb_date.month,
        })
        cb_idx += 1

    # ----- BASELINE PERIOD CHARGEBACKS -----
    # 30% unauthorized, 70% authorized (normal distribution)
    print(f"\nGenerating baseline chargebacks: {baseline_total}")

    # Get non-spike transactions
    baseline_txns = non_fastshop_txns[
        ~((non_fastshop_txns["txn_date"] >= SPIKE_START_DATE) &
          (non_fastshop_txns["txn_date"] <= SPIKE_END_DATE))
    ]

    # Sample baseline transactions
    if len(baseline_txns) >= baseline_total:
        selected_baseline = baseline_txns.sample(n=baseline_total, random_state=47)
    else:
        selected_baseline = baseline_txns.sample(n=baseline_total, replace=True, random_state=47)

    for _, txn in selected_baseline.iterrows():
        # 30% unauthorized during baseline
        is_unauthorized = rng.random() < BASELINE_TYPE_DISTRIBUTION.unauthorized

        if is_unauthorized:
            cb_type = ChargebackType.UNAUTHORIZED.value
            reasons = [r.value for r in BASELINE_UNAUTHORIZED_REASONS.keys()]
            weights = list(BASELINE_UNAUTHORIZED_REASONS.values())
            reason_code = str(rng.choice(reasons, p=np.array(weights)/sum(weights)))
        else:
            cb_type = ChargebackType.AUTHORIZED.value
            reasons = [r.value for r in AUTHORIZED_REASONS.keys()]
            weights = list(AUTHORIZED_REASONS.values())
            reason_code = str(rng.choice(reasons, p=np.array(weights)/sum(weights)))

        amount = int(rng.normal(BASELINE_AMOUNT_MEAN_CENTS, BASELINE_AMOUNT_STD_CENTS))
        amount = max(500, min(50000, amount))

        txn_date = txn["txn_date"]
        cb_offset = int(rng.integers(1, 45))
        cb_date = txn_date + timedelta(days=cb_offset)

        # Ensure baseline chargebacks don't fall in spike week
        while SPIKE_START_DATE <= cb_date <= SPIKE_END_DATE:
            cb_offset = int(rng.integers(1, 45))
            cb_date = txn_date + timedelta(days=cb_offset)
            # If we can't avoid spike week, place before it
            if SPIKE_START_DATE <= cb_date <= SPIKE_END_DATE:
                cb_date = SPIKE_START_DATE - timedelta(days=int(rng.integers(1, 30)))

        status = rng.choice(
            [ChargebackStatus.LOST.value, ChargebackStatus.PENDING.value, ChargebackStatus.WON.value, ChargebackStatus.EXPIRED.value],
            p=[0.40, 0.15, 0.40, 0.05]
        )

        resolution_date = None
        if status in [ChargebackStatus.LOST.value, ChargebackStatus.WON.value, ChargebackStatus.EXPIRED.value]:
            resolution_offset = int(rng.integers(14, 90))
            resolution_date = cb_date + timedelta(days=resolution_offset)

        currency = COUNTRY_CURRENCY.get(txn["country"], "EUR")

        records.append({
            "chargeback_id": generate_id("CB_", cb_idx, width=6),
            "transaction_id": txn["transaction_id"],
            "card_id": txn["card_id"],
            "merchant_id": txn["merchant_id"],
            "chargeback_date": cb_date,
            "chargeback_amount_cents": amount,
            "currency": currency,
            "chargeback_type": cb_type,
            "reason_code": reason_code,
            "status": status,
            "resolution_date": resolution_date,
            "year": cb_date.year,
            "month": cb_date.month,
        })
        cb_idx += 1

    df = pd.DataFrame(records)

    # Sort by chargeback date
    df = df.sort_values("chargeback_date").reset_index(drop=True)

    return df


def save_chargebacks(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Generate and save chargeback data."""
    print("Generating chargebacks with UC-2 pattern...")
    df = generate_chargebacks(transactions_df)
    output = write_parquet(df, "chargebacks", partition_cols=["year", "month"])

    print(f"\nWrote {len(df):,} chargebacks to {output}")

    # UC-2 validation
    fastshop_cbs = df[df["merchant_id"] == FASTSHOP_MERCHANT.merchant_id]
    spike_cbs = df[
        (df["chargeback_date"] >= SPIKE_START_DATE) &
        (df["chargeback_date"] <= SPIKE_END_DATE)
    ]
    spike_fastshop = fastshop_cbs[
        (fastshop_cbs["chargeback_date"] >= SPIKE_START_DATE) &
        (fastshop_cbs["chargeback_date"] <= SPIKE_END_DATE)
    ]
    spike_unauthorized = spike_cbs[spike_cbs["chargeback_type"] == ChargebackType.UNAUTHORIZED.value]
    spike_cnp = spike_unauthorized[spike_unauthorized["reason_code"] == ChargebackReasonCode.FRAUD_CARD_NOT_PRESENT.value]

    baseline_cbs = df[
        ~((df["chargeback_date"] >= SPIKE_START_DATE) &
          (df["chargeback_date"] <= SPIKE_END_DATE))
    ]
    baseline_unauthorized = baseline_cbs[baseline_cbs["chargeback_type"] == ChargebackType.UNAUTHORIZED.value]

    print(f"\n{'='*50}")
    print("UC-2 Pattern Validation:")
    print(f"{'='*50}")
    print(f"Total chargebacks: {len(df):,}")
    print(f"\nSpike period ({SPIKE_START_DATE} to {SPIKE_END_DATE}):")
    print(f"  Total: {len(spike_cbs):,}")
    print(f"  FastShop: {len(spike_fastshop):,} ({len(spike_fastshop)/len(spike_cbs)*100:.1f}% of spike)")
    print(f"  Unauthorized: {len(spike_unauthorized):,} ({len(spike_unauthorized)/len(spike_cbs)*100:.1f}%)")
    print(f"  CNP Fraud: {len(spike_cnp):,} ({len(spike_cnp)/len(spike_unauthorized)*100:.1f}% of unauthorized)")

    print("\nBaseline period:")
    print(f"  Total: {len(baseline_cbs):,}")
    print(f"  Unauthorized: {len(baseline_unauthorized):,} ({len(baseline_unauthorized)/len(baseline_cbs)*100:.1f}%)")

    daily_baseline = len(baseline_cbs) / ((DATA_END_DATE - DATA_START_DATE).days - 7)
    daily_spike = len(spike_cbs) / 7
    print("\nDaily rates:")
    print(f"  Baseline: {daily_baseline:.1f}/day")
    print(f"  Spike: {daily_spike:.1f}/day")
    print(f"  Spike multiplier: {daily_spike/daily_baseline:.2f}x")

    return df


if __name__ == "__main__":
    from .cards import generate_cards
    from .customers import generate_customers
    from .merchants import generate_merchants
    from .transactions import generate_transactions

    merchants_df = generate_merchants()
    customers_df = generate_customers()
    cards_df = generate_cards(customers_df)
    transactions_df = generate_transactions(cards_df, merchants_df, customers_df)
    save_chargebacks(transactions_df)
