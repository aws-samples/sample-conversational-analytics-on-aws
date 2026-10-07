# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Merchant data generator.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from faker import Faker

from conversational_analytics.patterns.chargeback_spike import FASTSHOP_MERCHANT
from conversational_analytics.schema_definitions import (
    MCC_CATEGORIES,
    TABLE_ROW_COUNTS,
    Country,
    MerchantChannel,
)

from .base import generate_id, set_seed, write_parquet

fake = Faker()
Faker.seed(42)


def generate_merchants(count: int | None = None) -> pd.DataFrame:
    """Generate merchant data including FastShop Online for UC-2."""
    count = count or TABLE_ROW_COUNTS["merchants"]
    rng = set_seed()

    # Reserve slot for FastShop
    regular_count = count - 1

    # MCC distribution
    mcc_codes = list(MCC_CATEGORIES.keys())
    mcc_weights = [1.0] * len(mcc_codes)
    # Boost common categories
    for i, code in enumerate(mcc_codes):
        if code in ["5411", "5812", "5541", "5814"]:  # Grocery, restaurant, gas, fast food
            mcc_weights[i] = 3.0
        elif code == "5964":  # Direct Marketing (e-commerce)
            mcc_weights[i] = 2.0

    mcc_probs = np.array(mcc_weights) / sum(mcc_weights)
    selected_mccs = rng.choice(mcc_codes, size=regular_count, p=mcc_probs)

    # Channel distribution: 55% POS, 35% ECOM, 10% ATM
    channels = [MerchantChannel.POS.value, MerchantChannel.ECOM.value, MerchantChannel.ATM.value]
    channel_weights = [0.55, 0.35, 0.10]
    selected_channels = rng.choice(channels, size=regular_count, p=channel_weights)

    # Country distribution for merchants
    countries = [c.value for c in Country]
    country_weights = [0.25, 0.20, 0.15, 0.12, 0.10, 0.07, 0.06, 0.05]  # ES, DE, UK, FR, IT, NL, PL, PT
    selected_countries = rng.choice(countries, size=regular_count, p=country_weights)

    # Generate merchant names
    merchant_names = [fake.company() for _ in range(regular_count)]

    # Build records
    records = []

    # Add FastShop first (critical for UC-2)
    records.append({
        "merchant_id": FASTSHOP_MERCHANT.merchant_id,
        "merchant_name": FASTSHOP_MERCHANT.merchant_name,
        "merchant_category_code": FASTSHOP_MERCHANT.merchant_category_code,
        "merchant_category_name": FASTSHOP_MERCHANT.merchant_category_name,
        "channel": FASTSHOP_MERCHANT.channel,
        "country": FASTSHOP_MERCHANT.country,
        "city": FASTSHOP_MERCHANT.city,
        "created_at": datetime(2024, 1, 1, 0, 0, 0),
    })

    # Add regular merchants
    created_at = datetime(2024, 1, 1, 0, 0, 0)
    for i in range(regular_count):
        mcc = selected_mccs[i]
        mcc_name = MCC_CATEGORIES[mcc][1]
        channel = selected_channels[i]
        country = selected_countries[i]

        # City for physical-location merchants (POS and ATM)
        city = fake.city() if channel in (MerchantChannel.POS.value, MerchantChannel.ATM.value) else None

        records.append({
            "merchant_id": generate_id("M_", i + 2, width=6),  # Start at 2, FastShop is 1
            "merchant_name": merchant_names[i],
            "merchant_category_code": mcc,
            "merchant_category_name": mcc_name,
            "channel": channel,
            "country": country,
            "city": city,
            "created_at": created_at,
        })

    df = pd.DataFrame(records)
    return df


def save_merchants() -> None:
    """Generate and save merchant data."""
    df = generate_merchants()
    output = write_parquet(df, "merchants")
    print(f"Wrote {len(df)} merchants to {output}")
    print(f"  FastShop Online: {df[df['merchant_id'] == FASTSHOP_MERCHANT.merchant_id]['merchant_name'].values[0]}")


if __name__ == "__main__":
    save_merchants()
