# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Customer data generator.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from datetime import date, datetime, timedelta

import pandas as pd
from faker import Faker

from conversational_analytics.schema_definitions import (
    COUNTRY_DISTRIBUTION,
    TABLE_ROW_COUNTS,
    CustomerType,
    MembershipTier,
    UserStatus,
)

from .base import distribute_counts, generate_id, set_seed, write_parquet

fake = Faker()
Faker.seed(42)


def generate_customers(count: int | None = None) -> pd.DataFrame:
    """Generate customer data with country distribution and segments."""
    count = count or TABLE_ROW_COUNTS["customers"]
    rng = set_seed()

    # Distribute customers across countries
    country_weights = {c.value: w for c, w in COUNTRY_DISTRIBUTION.items()}
    country_counts = distribute_counts(count, country_weights)

    # Membership tier distribution: 50% standard, 50% split among others (biased toward metal)
    membership_tiers = [
        MembershipTier.STANDARD.value,
        MembershipTier.PLUS.value,
        MembershipTier.GOLD.value,
        MembershipTier.METAL.value,
        MembershipTier.SELECT.value,
    ]
    membership_weights = [0.50, 0.10, 0.10, 0.20, 0.10]  # Metal gets highest of non-standard

    # 15% business customers
    business_rate = 0.15

    records = []
    customer_idx = 1

    # Registration date range: 2020-01-01 to 2025-12-31
    reg_start = date(2020, 1, 1)
    reg_end = date(2025, 12, 31)
    reg_days = (reg_end - reg_start).days

    created_at = datetime(2024, 1, 1, 0, 0, 0)

    for country, num_customers in country_counts.items():
        # Generate registration dates with slight recency bias
        reg_offsets = rng.beta(2, 5, size=num_customers) * reg_days
        registration_dates = [reg_start + timedelta(days=int(d)) for d in reg_offsets]

        # Generate membership tiers
        customer_tiers = rng.choice(membership_tiers, size=num_customers, p=membership_weights)
        is_business = rng.random(num_customers) < business_rate

        # Generate birth dates (18-80 years old as of 2025)
        ages = rng.integers(18, 80, size=num_customers)
        birth_years = 2025 - ages
        birth_months = rng.integers(1, 13, size=num_customers)
        birth_days = rng.integers(1, 29, size=num_customers)

        for i in range(num_customers):
            tier = customer_tiers[i]
            cust_type = CustomerType.BUSINESS.value if is_business[i] else CustomerType.PERSONAL.value

            # User status: standard 70% active, all others 95% active
            if tier == MembershipTier.STANDARD.value:
                user_status = UserStatus.ACTIVE.value if rng.random() < 0.70 else UserStatus.DORMANT.value
            else:
                user_status = UserStatus.ACTIVE.value if rng.random() < 0.95 else UserStatus.DORMANT.value

            dob = date(int(birth_years[i]), int(birth_months[i]), int(birth_days[i]))

            records.append({
                "customer_id": generate_id("C_", customer_idx, width=6),
                "email": fake.email(),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "date_of_birth": dob,
                "country": country,
                "customer_type": cust_type,
                "membership_tier": tier,
                "registration_date": registration_dates[i],
                "user_status": user_status,
                "created_at": created_at,
            })
            customer_idx += 1

    df = pd.DataFrame(records)

    # Shuffle to mix countries
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df


def save_customers() -> None:
    """Generate and save customer data partitioned by country."""
    df = generate_customers()
    output = write_parquet(df, "customers", partition_cols=["country"])

    print(f"Wrote {len(df)} customers to {output}")
    print("  Country distribution:")
    for country, count in df["country"].value_counts().sort_index().items():
        print(f"    {country}: {count} ({count/len(df)*100:.1f}%)")
    print("  Membership tier distribution:")
    for tier, count in df["membership_tier"].value_counts().items():
        print(f"    {tier}: {count} ({count/len(df)*100:.1f}%)")
    print(f"  Business customers: {(df['customer_type'] == 'business').sum()} ({(df['customer_type'] == 'business').mean()*100:.1f}%)")
    print(f"  Active users: {(df['user_status'] == 'active').sum()} ({(df['user_status'] == 'active').mean()*100:.1f}%)")


if __name__ == "__main__":
    save_customers()
