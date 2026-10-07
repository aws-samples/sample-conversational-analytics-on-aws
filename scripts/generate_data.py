#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Generate all synthetic data for Conversational Analytics.

Compliance note: all data is synthetic. The schemas model EU personal data
(names, email, date of birth) and payment card data (last four digits, transactions,
chargebacks). If you adapt this sample to real data, you are responsible for GDPR,
PCI DSS and any other applicable requirements.

Generates data in dependency order:
1. merchants (no dependencies)
2. customers (no dependencies)
3. cards (depends on customers)
4. transactions (depends on cards, merchants)
5. chargebacks (depends on transactions)

Usage:
    uv run python scripts/generate_data.py        # Default: Small (S) tier
    uv run python scripts/generate_data.py S      # Small - rapid iteration (~30s)
    uv run python scripts/generate_data.py M      # Medium - realistic testing (~5min)
    uv run python scripts/generate_data.py L      # Large - production-like (~30min)
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conversational_analytics.generators import (
    generate_cards,
    generate_chargebacks,
    generate_customers,
    generate_merchants,
    generate_tokenizations,
    generate_transactions,
    get_data_dir,
    write_parquet,
)
from conversational_analytics.schema_definitions import DataTier, get_row_counts


def main():
    # Parse tier argument
    tier_arg = sys.argv[1].upper() if len(sys.argv) > 1 else "S"
    try:
        tier = DataTier(tier_arg)
    except ValueError:
        print(f"Invalid tier: {tier_arg}. Use S, M, or L.")
        sys.exit(1)

    row_counts = get_row_counts(tier)

    start_time = time.time()
    print("=" * 60)
    print(f"Synthetic Data Generation - Tier {tier.value}")
    print("=" * 60)
    print(f"\nTier: {tier.value} ({'Small' if tier == DataTier.S else 'Medium' if tier == DataTier.M else 'Large'})")
    print(f"Output directory: {get_data_dir()}")
    print("\nTarget row counts:")
    for table, count in row_counts.items():
        print(f"  {table}: {count:,}")

    # 1. Merchants
    print("\n[1/6] Generating merchants...")
    t0 = time.time()
    merchants_df = generate_merchants(count=row_counts["merchants"])
    write_parquet(merchants_df, "merchants")
    print(f"  Generated {len(merchants_df):,} merchants in {time.time()-t0:.1f}s")

    # 2. Customers
    print("\n[2/6] Generating customers...")
    t0 = time.time()
    customers_df = generate_customers(count=row_counts["customers"])
    write_parquet(customers_df, "customers", partition_cols=["country"])
    print(f"  Generated {len(customers_df):,} customers in {time.time()-t0:.1f}s")

    # 3. Cards
    print("\n[3/6] Generating cards...")
    t0 = time.time()
    cards_df = generate_cards(customers_df)
    write_parquet(cards_df, "cards", partition_cols=["country", "year", "month"])
    print(f"  Generated {len(cards_df):,} cards in {time.time()-t0:.1f}s")

    # 4. Transactions
    print("\n[4/6] Generating transactions...")
    t0 = time.time()
    transactions_df = generate_transactions(
        cards_df, merchants_df, customers_df, count=row_counts["transactions"]
    )
    write_parquet(transactions_df, "transactions", partition_cols=["country", "year", "month"])
    print(f"  Generated {len(transactions_df):,} transactions in {time.time()-t0:.1f}s")

    # 5. Tokenizations
    print("\n[5/6] Generating tokenizations...")
    t0 = time.time()
    tokenizations_df = generate_tokenizations(
        cards_df, customers_df, count=row_counts["tokenizations"]
    )
    write_parquet(tokenizations_df, "tokenizations", partition_cols=["wallet_type"])
    print(f"  Generated {len(tokenizations_df):,} tokenizations in {time.time()-t0:.1f}s")

    # 6. Chargebacks
    print("\n[6/6] Generating chargebacks...")
    t0 = time.time()
    chargebacks_df = generate_chargebacks(transactions_df, target_count=row_counts["chargebacks"])
    write_parquet(chargebacks_df, "chargebacks", partition_cols=["year", "month"])
    print(f"  Generated {len(chargebacks_df):,} chargebacks in {time.time()-t0:.1f}s")

    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"\nTier: {tier.value}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"\nData written to: {get_data_dir()}")
    print("\nTable summary:")
    print(f"  merchants:      {len(merchants_df):>10,} rows")
    print(f"  customers:      {len(customers_df):>10,} rows")
    print(f"  cards:          {len(cards_df):>10,} rows")
    print(f"  transactions:   {len(transactions_df):>10,} rows")
    print(f"  tokenizations:  {len(tokenizations_df):>10,} rows")
    print(f"  chargebacks:    {len(chargebacks_df):>10,} rows")

    # UC-2 validation
    from conversational_analytics.patterns.chargeback_spike import (
        FASTSHOP_MERCHANT,
        SPIKE_END_DATE,
        SPIKE_START_DATE,
    )

    print("\n" + "=" * 60)
    print("UC-2 Chargeback Pattern Validation")
    print("=" * 60)

    fastshop_cbs = chargebacks_df[chargebacks_df["merchant_id"] == FASTSHOP_MERCHANT.merchant_id]
    spike_cbs = chargebacks_df[
        (chargebacks_df["chargeback_date"] >= SPIKE_START_DATE)
        & (chargebacks_df["chargeback_date"] <= SPIKE_END_DATE)
    ]
    spike_fastshop = fastshop_cbs[
        (fastshop_cbs["chargeback_date"] >= SPIKE_START_DATE)
        & (fastshop_cbs["chargeback_date"] <= SPIKE_END_DATE)
    ]
    spike_unauthorized = spike_cbs[spike_cbs["chargeback_type"] == "unauthorized"]

    print(f"\nSpike week ({SPIKE_START_DATE} to {SPIKE_END_DATE}):")
    print(f"  Chargebacks: {len(spike_cbs):,}")
    print(f"  FastShop: {len(spike_fastshop):,} ({len(spike_fastshop)/max(1,len(spike_cbs))*100:.1f}% of spike)")
    print(f"  Unauthorized: {len(spike_unauthorized):,} ({len(spike_unauthorized)/max(1,len(spike_cbs))*100:.1f}%)")

    # Check targets
    targets_met = []
    if len(spike_fastshop) / max(1, len(spike_cbs)) >= 0.75:
        targets_met.append("FastShop dominance (>75%)")
    if len(spike_unauthorized) / max(1, len(spike_cbs)) >= 0.80:
        targets_met.append("Unauthorized rate (>80%)")

    if len(targets_met) == 2:
        print("\n[OK] All UC-2 pattern targets met!")
    else:
        print(f"\n[WARNING] Some targets not met. Met: {targets_met}")


if __name__ == "__main__":
    main()
