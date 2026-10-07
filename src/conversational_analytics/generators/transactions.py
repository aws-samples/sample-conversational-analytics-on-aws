# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Transaction data generator with UC-2 spike pattern.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from conversational_analytics.patterns.chargeback_spike import (
    DATA_END_DATE,
    DATA_START_DATE,
    FASTSHOP_MERCHANT,
    SPIKE_END_DATE,
    SPIKE_START_DATE,
)
from conversational_analytics.schema_definitions import (
    MCC_DISTRIBUTION_METAL,
    MCC_DISTRIBUTION_REGULAR,
    TABLE_ROW_COUNTS,
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

# Transaction amount ranges by MCC (in cents)
MCC_AMOUNT_RANGES = {
    "5411": (500, 15000),      # Grocery: $5-$150
    "5541": (2000, 10000),     # Gas: $20-$100
    "5812": (1500, 20000),     # Restaurant: $15-$200
    "5814": (500, 3000),       # Fast food: $5-$30
    "4111": (200, 5000),       # Transport: $2-$50
    "3000": (10000, 150000),   # Airlines: $100-$1500
    "7011": (8000, 50000),     # Hotels: $80-$500
    "5912": (500, 10000),      # Pharmacy: $5-$100
    "5311": (2000, 20000),     # Department: $20-$200
    "5691": (2000, 25000),     # Clothing: $20-$250
    "5944": (5000, 100000),    # Jewelry: $50-$1000
    "5945": (1000, 15000),     # Toys: $10-$150
    "5732": (3000, 30000),     # Electronics: $30-$300
    "5999": (500, 8000),       # Misc retail: $5-$80
    "5964": (1000, 30000),     # Direct marketing/ecom: $10-$300
}


def _is_spike_period(d: date) -> bool:
    """Check if date is in spike period."""
    return SPIKE_START_DATE <= d <= SPIKE_END_DATE


def generate_transactions(
    cards_df: pd.DataFrame,
    merchants_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    count: int | None = None,
) -> pd.DataFrame:
    """Generate transaction data with UC-2 spike pattern.

    During spike week (2026-01-15 to 2026-01-21), 15% of transactions
    go to FastShop Online vs ~0.01% baseline.
    """
    count = count or TABLE_ROW_COUNTS["transactions"]
    rng = set_seed(seed=44)

    # Build lookups
    card_ids = cards_df[cards_df["is_active"]]["card_id"].to_numpy()
    card_countries = dict(zip(cards_df["card_id"], cards_df["country"]))
    card_customers = dict(zip(cards_df["card_id"], cards_df["customer_id"]))
    card_campaigns = dict(zip(cards_df["card_id"], cards_df["campaign_code"]))
    membership_tiers = dict(zip(customers_df["customer_id"], customers_df["membership_tier"]))

    # Separate merchants by MCC for segment-based selection
    merchants_by_mcc = merchants_df.groupby("merchant_category_code")["merchant_id"].apply(list).to_dict()
    fastshop_id = FASTSHOP_MERCHANT.merchant_id

    # Merchant MCC lookup
    merchant_mccs = dict(zip(merchants_df["merchant_id"], merchants_df["merchant_category_code"]))

    # Date range
    total_days = (DATA_END_DATE - DATA_START_DATE).days + 1

    # Distribute transactions across dates (slight weekday bias)
    dates = np.array([DATA_START_DATE + timedelta(days=i) for i in range(total_days)], dtype=object)

    # More transactions on weekdays
    raw_date_weights = []
    for d in dates:
        weight = 1.2 if d.weekday() < 5 else 0.8
        # Slight holiday boost in December
        if d.month == 12:
            weight *= 1.1
        raw_date_weights.append(weight)

    date_weights = np.array(raw_date_weights)
    date_weights /= date_weights.sum()

    # Assign transaction dates
    txn_dates = rng.choice(dates, size=count, p=date_weights)

    # Assign cards to transactions
    txn_cards = rng.choice(card_ids, size=count)

    records = []
    txn_idx = 1

    # Build MCC selection arrays for efficiency
    regular_mccs = list(MCC_DISTRIBUTION_REGULAR.keys())
    regular_weights = np.array([MCC_DISTRIBUTION_REGULAR[m] for m in regular_mccs])
    regular_weights /= regular_weights.sum()

    # Metal tier uses premium MCC distribution (travel, restaurants, etc.)
    metal_mccs = list(MCC_DISTRIBUTION_METAL.keys())
    metal_weights = np.array([MCC_DISTRIBUTION_METAL[m] for m in metal_mccs])
    metal_weights /= metal_weights.sum()

    # UC-5: XMAS_2025 MCC distribution — shifted toward Jewelry (5944) and Toys (5945)
    xmas_mccs = ["5944", "5945", "5812", "5311", "5691", "5732", "5999"]
    xmas_weights = np.array([0.18, 0.27, 0.15, 0.10, 0.10, 0.10, 0.10])
    xmas_weights = xmas_weights / xmas_weights.sum()

    # Process in batches for memory efficiency
    batch_size = 100000

    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        batch_dates = txn_dates[batch_start:batch_end]
        batch_cards = txn_cards[batch_start:batch_end]
        batch_size_actual = batch_end - batch_start

        # Determine which transactions go to FastShop (UC-2 pattern)
        is_spike = np.array([_is_spike_period(d) for d in batch_dates])
        spike_mask = is_spike & (rng.random(batch_size_actual) < 0.15)  # 15% during spike
        baseline_fastshop_mask = ~is_spike & (rng.random(batch_size_actual) < 0.0001)  # 0.01% baseline

        for i in range(batch_size_actual):
            txn_date = batch_dates[i]
            card_id = batch_cards[i]
            country = card_countries[card_id]
            customer_id = card_customers[card_id]
            tier = membership_tiers.get(customer_id, "standard")

            # UC-5: Check if card is XMAS_2025 campaign
            is_xmas = card_campaigns.get(card_id) == "XMAS_2025"

            # Determine merchant
            if spike_mask[i] or baseline_fastshop_mask[i]:
                merchant_id = fastshop_id
                mcc = FASTSHOP_MERCHANT.merchant_category_code
            elif is_xmas:
                # UC-5: XMAS cards shift toward Jewelry/Toys MCCs
                mcc = rng.choice(xmas_mccs, p=xmas_weights)
                if mcc in merchants_by_mcc and len(merchants_by_mcc[mcc]) > 0:
                    merchant_id = rng.choice(merchants_by_mcc[mcc])
                else:
                    merchant_id = rng.choice(merchants_df["merchant_id"].to_numpy())
                    mcc = merchant_mccs.get(merchant_id, "5999")
            else:
                # Select MCC based on membership tier
                if tier == "metal":
                    mcc = rng.choice(metal_mccs, p=metal_weights)
                else:
                    mcc = rng.choice(regular_mccs, p=regular_weights)

                # Select random merchant from that MCC
                if mcc in merchants_by_mcc and len(merchants_by_mcc[mcc]) > 0:
                    merchant_id = rng.choice(merchants_by_mcc[mcc])
                else:
                    # Fallback to any merchant
                    merchant_id = rng.choice(merchants_df["merchant_id"].to_numpy())
                    mcc = merchant_mccs.get(merchant_id, "5999")

            # Amount based on MCC
            min_amt, max_amt = MCC_AMOUNT_RANGES.get(mcc, (1000, 20000))
            # Log-normal for realistic distribution (skewed toward lower amounts)
            mean_amt = (min_amt + max_amt) / 2
            amount = int(rng.lognormal(np.log(mean_amt / 2), 0.8))
            amount = max(min_amt, min(max_amt, amount))

            # Metal tier customers spend more
            if tier == "metal":
                amount = int(amount * rng.uniform(1.3, 2.0))

            # UC-5: XMAS_2025 cardholders already spend more due to MCC shift
            # toward Jewelry/Toys (higher-value categories).
            # No additional multiplier needed — the category shift provides the lift.

            # Currency
            currency = COUNTRY_CURRENCY.get(country, "EUR")

            # Authorization
            is_approved = rng.random() < 0.97  # 97% approval rate
            decline_reason = None
            if not is_approved:
                decline_reason = rng.choice([
                    "insufficient_funds",
                    "card_expired",
                    "suspected_fraud",
                    "invalid_cvv",
                ])

            # Transaction time
            hour = rng.integers(8, 23)
            minute = rng.integers(0, 60)
            second = rng.integers(0, 60)
            txn_datetime = datetime(
                txn_date.year, txn_date.month, txn_date.day,
                hour, minute, second
            )

            # Auth code
            auth_code = f"AUTH{rng.integers(100000, 999999)}" if is_approved else None

            records.append({
                "transaction_id": generate_id("TXN_", txn_idx, width=9),
                "card_id": card_id,
                "merchant_id": merchant_id,
                "amount_cents": amount,
                "currency": currency,
                "transaction_date": txn_datetime,
                "authorization_code": auth_code,
                "is_approved": is_approved,
                "decline_reason": decline_reason,
                "country": country,
                "year": txn_date.year,
                "month": txn_date.month,
            })
            txn_idx += 1

        if batch_end % 500000 == 0:
            print(f"  Generated {batch_end:,} transactions...")

    df = pd.DataFrame(records)
    return df


def save_transactions(
    cards_df: pd.DataFrame,
    merchants_df: pd.DataFrame,
    customers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate and save transaction data."""
    print("Generating transactions (this may take a few minutes)...")
    df = generate_transactions(cards_df, merchants_df, customers_df)
    output = write_parquet(df, "transactions", partition_cols=["country", "year", "month"])

    print(f"Wrote {len(df):,} transactions to {output}")

    # UC-2 validation
    fastshop_txns = df[df["merchant_id"] == FASTSHOP_MERCHANT.merchant_id]
    spike_txns = df[
        (df["transaction_date"].dt.date >= SPIKE_START_DATE) &
        (df["transaction_date"].dt.date <= SPIKE_END_DATE)
    ]
    spike_fastshop = fastshop_txns[
        (fastshop_txns["transaction_date"].dt.date >= SPIKE_START_DATE) &
        (fastshop_txns["transaction_date"].dt.date <= SPIKE_END_DATE)
    ]

    print("\nUC-2 Pattern Validation:")
    print(f"  Total FastShop transactions: {len(fastshop_txns):,}")
    print(f"  Spike week transactions: {len(spike_txns):,}")
    print(f"  FastShop during spike: {len(spike_fastshop):,}")
    if len(spike_txns) > 0:
        print(f"  FastShop % during spike: {len(spike_fastshop)/len(spike_txns)*100:.1f}%")

    return df


if __name__ == "__main__":
    from .cards import generate_cards
    from .customers import generate_customers
    from .merchants import generate_merchants

    merchants_df = generate_merchants()
    customers_df = generate_customers()
    cards_df = generate_cards(customers_df)
    save_transactions(cards_df, merchants_df, customers_df)
