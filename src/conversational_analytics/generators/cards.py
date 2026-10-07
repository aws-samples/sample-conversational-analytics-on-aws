# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Card data generator.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from conversational_analytics.schema_definitions import (
    CardType,
    DeliveryType,
    OrderType,
)

from .base import generate_id, set_seed, write_parquet


def generate_cards(
    customers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate card data linked to customers.

    Args:
        customers_df: DataFrame with customer data (needs customer_id, country, registration_date)
    """
    rng = set_seed(seed=43)  # Different seed than customers

    customer_ids = customers_df["customer_id"].to_numpy()
    customer_countries = dict(zip(customers_df["customer_id"], customers_df["country"]))
    customer_reg_dates = dict(zip(customers_df["customer_id"], customers_df["registration_date"]))
    customer_types = dict(zip(customers_df["customer_id"], customers_df["customer_type"]))

    membership_tiers = dict(zip(customers_df["customer_id"], customers_df["membership_tier"]))

    # UC-6: Spanish business metal users average ~2.3 active cards, personal ~1.1.
    # Each customer gets 1 + Poisson(extra) cards (mean 1 + extra). Counts are NOT
    # rescaled to a fixed total, since that would distort these averages; the card
    # volume follows from the customer mix (~1.25 cards per customer).
    cards_per_customer = np.empty(len(customer_ids), dtype=int)
    for i, cid in enumerate(customer_ids):
        ctype = customer_types[cid]
        country = customer_countries[cid]
        tier = membership_tiers.get(cid, "standard")
        if ctype == "business" and country == "ES" and tier == "metal":
            extra = 1.35  # ~2.35 cards, ~2.3 active after the 98% activation rate
        elif ctype == "business":
            extra = 0.8
        elif tier == "metal":
            extra = 0.2
        else:
            extra = 0.1
        cards_per_customer[i] = 1 + int(rng.poisson(lam=extra))

    # Card type distribution: 70% physical, 30% virtual
    card_types = [CardType.PHYSICAL.value, CardType.VIRTUAL.value]
    card_type_weights = [0.70, 0.30]

    # Network: 100% Mastercard
    network = "mastercard"

    # Campaign codes: 3% XMAS_2025, 2% other campaigns
    campaign_codes = np.array([None, "XMAS_2025", "SUMMER_2025", "WELCOME_2025"], dtype=object)
    campaign_weights = [0.95, 0.03, 0.01, 0.01]

    created_at = datetime(2024, 1, 1, 0, 0, 0)

    records = []
    card_idx = 1

    for cust_idx, num_cards in enumerate(cards_per_customer):
        customer_id = customer_ids[cust_idx]
        country = customer_countries[customer_id]
        reg_date = customer_reg_dates[customer_id]

        # Convert reg_date to date if needed
        if isinstance(reg_date, datetime):
            reg_date = reg_date.date()

        for card_num in range(num_cards):
            card_type = rng.choice(card_types, p=card_type_weights)
            campaign = rng.choice(campaign_codes, p=campaign_weights)

            # Issue date: between registration and 2025-12-31
            max_issue_days = (date(2025, 12, 31) - reg_date).days
            issue_offset = int(rng.integers(0, max(1, max_issue_days)))
            issue_date = reg_date + timedelta(days=issue_offset)

            # Expiry: 3-5 years from issue
            expiry_years = rng.choice([3, 4, 5], p=[0.3, 0.4, 0.3])
            expiry_date = date(issue_date.year + expiry_years, issue_date.month, 1)

            # UC-4: delivery_type — ~30% express, ~70% standard
            delivery_type = rng.choice(
                [DeliveryType.EXPRESS.value, DeliveryType.STANDARD.value],
                p=[0.30, 0.70],
            )

            # UC-4: Delivery days split by express/standard and country
            if delivery_type == DeliveryType.EXPRESS.value:
                if country == "DE":
                    delivery_days = int(rng.integers(7, 10))   # express ~8 days
                elif country == "ES":
                    delivery_days = int(rng.integers(2, 5))    # express ~3 days
                elif country == "UK":
                    delivery_days = int(rng.integers(4, 7))    # express ~5 days
                else:
                    delivery_days = int(rng.integers(3, 6))    # express ~4 days
            else:  # standard
                if country == "DE":
                    delivery_days = int(rng.integers(13, 18))  # standard ~15 days
                elif country == "ES":
                    delivery_days = int(rng.integers(5, 10))   # standard ~7 days
                elif country == "UK":
                    delivery_days = int(rng.integers(8, 13))   # standard ~10 days
                else:
                    delivery_days = int(rng.integers(7, 12))   # standard ~9 days

            delivery_date = issue_date + timedelta(days=delivery_days)

            # UC-4: order_type — first card is "initial", subsequent are reorder/replacement/additional
            if card_num == 0:
                order_type = OrderType.INITIAL.value
            else:
                order_type = rng.choice(
                    [OrderType.REORDER.value, OrderType.REPLACEMENT_EXPIRED.value, OrderType.ADDITIONAL.value],
                    p=[0.50, 0.20, 0.30],
                )

            # 98% of cards are activated
            is_activated = rng.random() < 0.98

            if is_activated:
                # UC-4: activation_date — days after delivery (varies by delivery type and country)
                if delivery_type == DeliveryType.EXPRESS.value:
                    activation_offset = int(rng.integers(1, 6))   # 1-5 days
                else:
                    activation_offset = int(rng.integers(1, 15))  # 1-14 days
                activation_date = delivery_date + timedelta(days=activation_offset)
                is_active = True
            else:
                activation_date = None
                is_active = False

            # Last 4 digits
            last_four = f"{rng.integers(0, 10000):04d}"

            records.append({
                "card_id": generate_id("CARD_", card_idx, width=6),
                "customer_id": customer_id,
                "card_type": card_type,
                "card_network": network,
                "last_four_digits": last_four,
                "expiry_date": expiry_date,
                "issue_date": issue_date,
                "delivery_date": delivery_date,
                "delivery_type": delivery_type,
                "order_type": order_type,
                "activation_date": activation_date,
                "country": country,
                "year": issue_date.year,
                "month": issue_date.month,
                "campaign_code": campaign,
                "is_active": is_active,
                "created_at": created_at,
            })
            card_idx += 1

    df = pd.DataFrame(records)
    return df


def save_cards(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Generate and save card data partitioned by country/year/month."""
    df = generate_cards(customers_df)
    output = write_parquet(df, "cards", partition_cols=["country", "year", "month"])

    print(f"Wrote {len(df)} cards to {output}")
    print("  Card type distribution:")
    for ct, count in df["card_type"].value_counts().items():
        print(f"    {ct}: {count} ({count/len(df)*100:.1f}%)")
    activated_count = df["activation_date"].notna().sum()
    print(f"  Activated cards: {activated_count} ({activated_count/len(df)*100:.1f}%)")
    print(f"  XMAS_2025 cards: {(df['campaign_code'] == 'XMAS_2025').sum()}")

    return df


if __name__ == "__main__":
    from .customers import generate_customers
    customers_df = generate_customers()
    save_cards(customers_df)
