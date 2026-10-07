# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tokenization data generator (UC-1).

Business Question: "How long after joining should we push users to tokenize?"

Expected Discovery Path:
1. ES: 3 days (fast adopters, 80th percentile)
2. DE: 12 days (slow adopters)
3. UK: 7 days (medium)
4. Other countries fall between 6-10 days

Uses gamma distribution for realistic right-skewed timing distributions.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from datetime import datetime, timedelta

import pandas as pd

from conversational_analytics.schema_definitions import TABLE_ROW_COUNTS, WalletType

from .base import generate_id, set_seed, write_parquet

# Country-based timing targets (80th percentile in days)
# Gamma distribution shape/scale tuned to hit these targets
COUNTRY_TOKENIZATION_TIMING: dict[str, dict[str, float]] = {
    "ES": {"shape": 2.0, "scale": 1.0},   # 80th pctl ~3 days (fast adopters)
    "DE": {"shape": 2.5, "scale": 3.3},   # 80th pctl ~12 days (slow adopters)
    "UK": {"shape": 2.2, "scale": 2.2},   # 80th pctl ~7 days (medium)
    "FR": {"shape": 2.2, "scale": 2.7},   # 80th pctl ~8 days
    "IT": {"shape": 2.3, "scale": 2.8},   # 80th pctl ~9 days
    "NL": {"shape": 2.0, "scale": 2.3},   # 80th pctl ~6 days
    "PL": {"shape": 2.5, "scale": 2.7},   # 80th pctl ~9 days
    "PT": {"shape": 2.2, "scale": 3.3},   # 80th pctl ~10 days
}

# Default for any unlisted country
DEFAULT_TIMING = {"shape": 2.2, "scale": 3.0}

# Wallet type distribution
WALLET_DISTRIBUTION = {
    WalletType.APPLE_PAY.value: 0.48,
    WalletType.GOOGLE_PAY.value: 0.33,
    WalletType.SAMSUNG_PAY.value: 0.14,
    WalletType.GARMIN_PAY.value: 0.05,
}

# Token requestor IDs per wallet type
TOKEN_REQUESTOR_IDS = {
    WalletType.APPLE_PAY.value: "TR_APPLE_001",
    WalletType.GOOGLE_PAY.value: "TR_GOOGLE_001",
    WalletType.SAMSUNG_PAY.value: "TR_SAMSUNG_001",
    WalletType.GARMIN_PAY.value: "TR_GARMIN_001",
}

# ~60% of cards get tokenized
TOKENIZATION_RATE = 0.60


def generate_tokenizations(
    cards_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    count: int | None = None,
) -> pd.DataFrame:
    """Generate tokenization records linked to cards.

    Args:
        cards_df: DataFrame with card data (needs card_id, customer_id, country)
        customers_df: DataFrame with customer data (needs customer_id, registration_date)
        count: Target number of tokenization records
    """
    count = count or TABLE_ROW_COUNTS["tokenizations"]
    rng = set_seed(seed=46)

    # Build lookups
    customer_reg_dates = dict(
        zip(customers_df["customer_id"], customers_df["registration_date"])
    )
    card_countries = dict(zip(cards_df["card_id"], cards_df["country"]))
    card_customers = dict(zip(cards_df["card_id"], cards_df["customer_id"]))

    # Select cards to tokenize (~60% rate)
    active_cards = cards_df[cards_df["is_active"]]["card_id"].to_numpy()
    n_eligible = len(active_cards)
    n_tokenize = min(count, int(n_eligible * TOKENIZATION_RATE))

    # Scale up if target count exceeds eligible cards at 60%
    if count > n_tokenize:
        n_tokenize = min(count, n_eligible)

    selected_cards = rng.choice(active_cards, size=n_tokenize, replace=False)

    # Wallet type arrays
    wallet_types = list(WALLET_DISTRIBUTION.keys())
    wallet_weights = list(WALLET_DISTRIBUTION.values())

    records = []
    tok_idx = 1

    for card_id in selected_cards:
        country = card_countries[card_id]
        customer_id = card_customers[card_id]
        reg_date = customer_reg_dates.get(customer_id)

        if reg_date is None:
            continue

        # Convert to date if needed
        if isinstance(reg_date, datetime):
            reg_date = reg_date.date()

        # Country-based gamma distribution for days_to_tokenize
        timing = COUNTRY_TOKENIZATION_TIMING.get(country, DEFAULT_TIMING)
        days_raw = rng.gamma(shape=timing["shape"], scale=timing["scale"])
        days_to_tokenize = max(1, int(round(days_raw)))

        # Tokenization date = registration_date + days_to_tokenize
        tok_date = reg_date + timedelta(days=days_to_tokenize)
        tok_datetime = datetime(
            tok_date.year, tok_date.month, tok_date.day,
            int(rng.integers(8, 22)),  # business hours
            int(rng.integers(0, 60)),
            int(rng.integers(0, 60)),
        )

        # Wallet type
        wallet_type = rng.choice(wallet_types, p=wallet_weights)
        token_requestor_id = TOKEN_REQUESTOR_IDS[wallet_type]

        records.append({
            "tokenization_id": generate_id("TOK_", tok_idx, width=6),
            "card_id": card_id,
            "wallet_type": wallet_type,
            "token_requestor_id": token_requestor_id,
            "tokenization_date": tok_datetime,
            "customer_registration_date": reg_date,
            "days_to_tokenize": days_to_tokenize,
        })
        tok_idx += 1

    df = pd.DataFrame(records)
    return df


def save_tokenizations(
    cards_df: pd.DataFrame,
    customers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate and save tokenization data partitioned by wallet_type."""
    df = generate_tokenizations(cards_df, customers_df)
    output = write_parquet(df, "tokenizations", partition_cols=["wallet_type"])

    print(f"Wrote {len(df):,} tokenizations to {output}")
    print("  Wallet type distribution:")
    for wt, cnt in df["wallet_type"].value_counts().items():
        print(f"    {wt}: {cnt:,} ({cnt/len(df)*100:.1f}%)")

    # UC-1 validation: check 80th percentile by country
    print("\nUC-1 Pattern Validation (80th percentile days_to_tokenize):")
    for country in ["ES", "DE", "UK", "FR", "IT"]:
        subset = df[df["card_id"].map(
            dict(zip(cards_df["card_id"], cards_df["country"]))
        ) == country]
        if len(subset) > 0:
            p80 = subset["days_to_tokenize"].quantile(0.80)
            print(f"    {country}: {p80:.0f} days")

    return df


if __name__ == "__main__":
    from .cards import generate_cards
    from .customers import generate_customers

    customers_df = generate_customers()
    cards_df = generate_cards(customers_df)
    save_tokenizations(cards_df, customers_df)
