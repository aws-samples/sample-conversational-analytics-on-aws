# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
QuickSight Q Topic synonym definitions for Conversational Analytics.

This module contains all synonym mappings for columns and cell values,
extracted from the PM-approved docs/synonyms-for-review.md document.

These synonyms enable natural language queries in QuickSight Q to match
user terminology with the underlying data model.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

# =============================================================================
# COUNTRY SYNONYMS (shared across all country columns)
# =============================================================================

COUNTRY_SYNONYMS: dict[str, list[str]] = {
    "ES": ["Spain", "Spanish", "España", "Espana", "ESP"],
    "DE": ["Germany", "German", "Deutschland", "DEU"],
    "UK": ["United Kingdom", "Britain", "British", "England", "GB"],
    "FR": ["France", "French", "FRA"],
    "IT": ["Italy", "Italian", "Italia", "ITA"],
    "NL": ["Netherlands", "Dutch", "Holland", "NLD"],
    "PL": ["Poland", "Polish", "Polska", "POL"],
    "PT": ["Portugal", "Portuguese", "POR"],
}

# =============================================================================
# COLUMN SYNONYMS BY TABLE
# =============================================================================
# Maps: {table_name: {column_name: [synonyms]}}

COLUMN_SYNONYMS: dict[str, dict[str, list[str]]] = {
    "customers": {
        "customer_id": ["user ID", "account ID", "client ID"],
        "customer_type": ["account type", "client type", "user type"],
        "membership_tier": ["tier", "membership", "membership level", "plan", "subscription"],
        "user_status": ["status", "activity status", "account status"],
        "registration_date": ["signup date", "join date", "enrollment date"],
        "country": ["customer country", "region", "location"],
    },
    "cards": {
        "card_id": ["card number", "card identifier"],
        "card_type": ["form factor", "card form"],
        "card_network": ["network", "payment network", "brand"],
        "issue_date": ["issuance date", "card issue date"],
        "delivery_date": ["shipping date", "arrival date"],
        "delivery_type": ["shipping type", "delivery speed", "shipping speed"],
        "order_type": ["order reason", "card order type"],
        "activation_date": ["activation", "first use date"],
        "campaign_code": ["promo code", "promotion", "campaign", "special edition"],
        "is_active": ["active status", "card status", "active"],
        "country": ["card country", "region"],
    },
    "transactions": {
        "transaction_id": ["txn ID", "payment ID"],
        "amount_cents": [
            "amount",
            "transaction amount",
            "purchase amount",
            "spend",
            "value",
            "total",
        ],
        "transaction_date": ["date", "purchase date", "payment date", "txn date"],
        "is_approved": ["approved", "successful", "completed", "authorized"],
        "decline_reason": ["rejection reason", "failure reason"],
        "country": ["transaction country", "purchase country"],
    },
    "tokenizations": {
        "tokenization_id": ["token ID"],
        "wallet_type": [
            "digital wallet",
            "wallet",
            "mobile wallet",
            "payment wallet",
        ],
        "tokenization_date": ["provisioning date", "token date", "wallet setup date"],
        "days_to_tokenize": [
            "time to tokenize",
            "tokenization timing",
            "days until tokenization",
            "wallet activation time",
            "days to provision",
        ],
        "customer_registration_date": ["registration date", "signup date"],
    },
    "chargebacks": {
        "chargeback_id": ["dispute ID", "CB ID"],
        "chargeback_date": ["dispute date", "filing date", "CB date"],
        "chargeback_amount_cents": [
            "dispute amount",
            "CB amount",
            "chargeback value",
            "disputed amount",
        ],
        "chargeback_type": ["dispute type", "CB type", "fraud type"],
        "reason_code": ["dispute reason", "CB reason", "chargeback reason"],
        "status": ["dispute status", "resolution status", "CB status"],
        "resolution_date": ["resolved date", "closure date"],
    },
    "merchants": {
        "merchant_id": ["store ID", "vendor ID", "seller ID"],
        "merchant_name": ["store name", "vendor name", "business name", "shop name"],
        "merchant_category_code": [
            "MCC",
            "category code",
            "industry code",
            "merchant category",
        ],
        "merchant_category_name": ["category", "industry", "business type"],
        "channel": ["sales channel", "transaction channel", "purchase channel"],
        "country": ["merchant country", "store country"],
        "city": ["merchant city", "store location"],
    },
}

# =============================================================================
# CELL VALUE SYNONYMS BY TABLE AND COLUMN
# =============================================================================
# Maps: {table_name: {column_name: {cell_value: [synonyms]}}}

CELL_VALUE_SYNONYMS: dict[str, dict[str, dict[str, list[str]]]] = {
    "customers": {
        "membership_tier": {
            "standard": [
                "std",
                "free account",
                "free tier",
                "basic",
                "free plan",
            ],
            "plus": [
                "plus tier",
                "plus plan",
            ],
            "gold": [
                "gold tier",
                "gold plan",
            ],
            "metal": [
                "metal tier",
                "premium",
                "metal plan",
            ],
            "select": [
                "select tier",
                "select plan",
            ],
        },
        "customer_type": {
            "personal": [
                "individual",
                "consumer",
                "retail customer",
                "private customer",
                "B2C",
                "Perso",
            ],
            "business": [
                "corporate",
                "company",
                "B2B",
                "commercial",
                "SMB",
                "business account",
                "Biz",
            ],
        },
        "user_status": {
            "active": [
                "MAU",
                "monthly active users",
                "engaged users",
                "current users",
            ],
            "dormant": [
                "inactive users",
                "churned customers",
                "lapsed users",
                "sleeping accounts",
                "non-active",
                "Non MAU",
            ],
        },
    },
    "cards": {
        "card_type": {
            "virtual": ["digital card", "virtual card", "digital-only", "e-card"],
            "physical": ["plastic card", "physical card", "tangible card"],
        },
        "card_network": {
            "mastercard": ["MC", "Mastercard", "Master Card"],
        },
        "delivery_type": {
            "express": [
                "fast delivery",
                "priority shipping",
                "expedited",
                "rush delivery",
                "next-day",
                "quick delivery",
            ],
            "standard": [
                "normal delivery",
                "regular shipping",
                "standard shipping",
                "economy delivery",
            ],
        },
        "order_type": {
            "initial": ["first card", "Bundle card", "bundled card", "membership card"],
            "reorder": ["replacement", "re-issue", "new copy", "duplicate"],
            "replacement_expired": [
                "expired replacement",
                "renewal",
                "expiry replacement",
                "card renewal",
            ],
            "additional": [
                "extra card",
                "second card",
                "supplementary card",
                "added card",
                "non bundled",
            ],
        },
        "campaign_code": {
            "XMAS_2025": [
                "Xmas card",
                "Christmas card",
                "Christmas special",
                "holiday edition",
                "Christmas 2025",
                "special edition",
                "limited edition",
                "Xmas special",
            ],
        },
    },
    "transactions": {
        "is_approved": {
            "true": ["successful", "completed", "authorized", "accepted", "processed", "Presentment", "authorization"],
            "false": [
                "rejected",
                "failed",
                "denied",
                "unsuccessful",
                "blocked",
                "declined",
            ],
        },
    },
    "tokenizations": {
        "wallet_type": {
            "apple_pay": [
                "Apple Wallet",
                "iOS Pay",
                "iPhone wallet",
                "Apple payment",
            ],
            "google_pay": [
                "GPay",
                "Google Wallet",
                "Android Pay",
                "Google payment",
            ],
            "samsung_pay": ["Samsung Wallet", "Samsung payment"],
            "garmin_pay": ["Garmin Wallet", "Runner wallet"],
        },
    },
    "chargebacks": {
        "chargeback_type": {
            "unauthorized": [
                "fraud",
                "fraudulent transaction",
                "not authorized",
                "stolen card",
                "fraud dispute",
                "unauthorized transaction",
                "Unauth",
            ],
            "authorized": [
                "legitimate dispute",
                "non-fraud dispute",
                "merchant dispute",
                "service dispute",
                "product dispute",
                "auth",
            ],
        },
        "reason_code": {
            "fraud_card_not_present": [
                "CNP fraud",
                "online fraud",
                "remote fraud",
                "card-not-present",
                "e-commerce fraud",
            ],
            "fraud_counterfeit": [
                "fake card",
                "cloned card",
                "counterfeit card",
                "skimmed card",
                "card cloning",
            ],
            "fraud_lost_stolen": [
                "lost card",
                "stolen card",
                "missing card",
                "card theft",
            ],
            "merchandise_not_received": [
                "item not received",
                "goods not delivered",
                "non-delivery",
                "package not arrived",
                "missing order",
                "Service not received",
            ],
            "merchandise_defective": [
                "defective item",
                "damaged goods",
                "broken product",
                "faulty merchandise",
                "quality issue",
                "Goods not as described",
            ],
            "duplicate_charge": [
                "double charge",
                "charged twice",
                "duplicate transaction",
                "double billing",
                "Duplicate processing",
            ],
            "incorrect_amount": [
                "wrong amount",
                "overcharge",
                "billing error",
                "amount mismatch",
                "Difference in amount",
                "unreasonable amount",
            ],
            "subscription_cancelled": [
                "cancelled subscription",
                "recurring charge after cancel",
                "unwanted renewal",
                "subscription dispute",
            ],
        },
        "status": {
            "pending": [
                "open",
                "in progress",
                "under review",
                "unresolved",
                "active dispute",
            ],
            "won": [
                "User won",
                "refunded",
                "accepted",
                "merchant lost",
            ],
            "lost": [
                "User lost",
                "not refunded",
                "rejected",
                "merchant won",
            ],
            "expired": ["timed out", "closed", "expired dispute", "No response"],
        },
    },
    "merchants": {
        "channel": {
            "pos": [
                "in-store",
                "point of sale",
                "retail",
                "physical store",
                "brick and mortar",
                "in-person",
                "chip and pin",
            ],
            "ecom": [
                "online",
                "e-commerce",
                "web purchase",
                "internet purchase",
                "digital",
                "online store",
            ],
            "atm": [
                "Withdraw",
                "cash machine",
                "Geldautomat",
            ],
        },
        # MCC synonyms - map MCC codes to common names
        "merchant_category_code": {
            "5411": ["groceries", "grocery stores", "supermarket", "food shopping"],
            "5541": [
                "gas stations",
                "petrol stations",
                "fuel",
                "gas",
                "filling station",
                "service station",
            ],
            "5812": [
                "restaurants",
                "dining",
                "eating out",
                "restaurant spending",
                "food & beverage",
            ],
            "5814": [
                "fast food",
                "quick service",
                "QSR",
                "fast casual",
                "takeaway",
                "takeout",
            ],
            "3000": [
                "airlines",
                "flights",
                "air travel",
                "airline tickets",
                "flight purchases",
            ],
            "7011": [
                "hotels",
                "accommodation",
                "lodging",
                "hotel bookings",
                "hospitality",
            ],
            "4722": [
                "travel",
                "travel agencies",
                "vacation",
                "trips",
                "travel bookings",
            ],
            "5912": ["pharmacies", "drugstore", "chemist", "pharmacy purchases"],
            "5311": [
                "department stores",
                "department store",
                "big-box retail",
                "general merchandise",
            ],
            "5691": [
                "clothing stores",
                "apparel",
                "fashion",
                "clothes shopping",
                "clothing retail",
            ],
            "5944": [
                "jewelry stores",
                "jewelry",
                "jewellery",
                "accessories",
                "watch stores",
            ],
            "5945": ["toy stores", "toys", "games", "toy shops", "children's retail"],
            "5732": [
                "electronics",
                "electronics stores",
                "tech",
                "gadgets",
                "consumer electronics",
            ],
            "5964": [
                "direct marketing",
                "e-commerce",
                "online retail",
                "direct sales",
            ],
        },
        # Specific merchant names for demo
        "merchant_name": {
            "FastShop Online": [
                "FastShop",
                "the fraudulent merchant",
                "problematic merchant",
            ],
        },
    },
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_column_synonyms(table_name: str, column_name: str) -> list[str]:
    """Get synonyms for a specific column.

    Args:
        table_name: Name of the table (e.g., 'customers')
        column_name: Name of the column (e.g., 'membership_tier')

    Returns:
        List of synonym strings, or empty list if none defined
    """
    return COLUMN_SYNONYMS.get(table_name, {}).get(column_name, [])


def get_cell_value_synonyms(
    table_name: str, column_name: str
) -> dict[str, list[str]]:
    """Get cell value synonyms for a specific column.

    Args:
        table_name: Name of the table (e.g., 'customers')
        column_name: Name of the column (e.g., 'membership_tier')

    Returns:
        Dict mapping cell values to their synonyms, or empty dict if none defined
    """
    return CELL_VALUE_SYNONYMS.get(table_name, {}).get(column_name, {})


def is_country_column(column_name: str) -> bool:
    """Check if a column is a country column that should get country synonyms."""
    return column_name == "country"
