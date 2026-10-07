# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
QuickSight Q Topic synonym definitions for pre-joined Conversational Analytics datasets.

This module contains synonyms specific to the optimized Q Topic that uses
pre-joined datasets (spending-analysis, tokenization-analysis, etc.).

The column names may differ from raw tables due to aliasing in JOINs
(e.g., customer_country vs country, merchant_category vs category_name).
"""

# =============================================================================
# COUNTRY SYNONYMS (reused from topic_synonyms.py)
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
# COLUMN SYNONYMS FOR JOINED DATASETS
# =============================================================================

JOINED_COLUMN_SYNONYMS: dict[str, dict[str, list[str]]] = {
    "spending-analysis": {
        # Transaction columns
        "amount_cents": [
            "amount",
            "transaction amount",
            "purchase amount",
            "spend",
            "spending",
            "value",
            "total",
        ],
        "transaction_date": ["date", "purchase date", "payment date"],
        "is_approved": ["approved", "successful", "completed"],
        # Card columns
        "card_type": ["form factor", "card form"],
        "campaign_code": ["promo code", "promotion", "campaign", "special edition", "XMAS", "Christmas"],
        "card_is_active": ["active card", "card active"],
        # Customer columns
        "customer_country": ["country", "customer location", "region"],
        "customer_type": ["account type", "client type"],
        "membership_tier": ["tier", "membership", "membership level", "plan"],
        # Merchant columns
        "merchant_name": ["merchant", "store", "shop", "vendor"],
        "mcc": ["category code", "MCC code", "merchant code"],
        "merchant_category": ["category", "merchant type", "business type", "industry"],
        "merchant_channel": ["merchant type", "store type"],
        "merchant_country": ["merchant location", "store country"],
    },
    "tokenization-analysis": {
        # Tokenization columns
        "wallet_type": ["digital wallet", "wallet", "mobile wallet", "payment wallet"],
        "tokenization_date": ["provisioning date", "token date", "wallet setup date"],
        "days_to_tokenize": [
            "time to tokenize",
            "tokenization timing",
            "days until tokenization",
            "wallet activation time",
            "days to provision",
            "tokenization delay",
        ],
        # Card columns
        "card_type": ["form factor", "card form"],
        "card_issue_date": ["issue date", "card date"],
        # Customer columns
        "country": ["customer country", "region", "location"],
        "customer_type": ["account type", "client type"],
        "membership_tier": ["tier", "membership", "membership level", "plan"],
        "registration_date": ["signup date", "join date", "enrollment date", "KYC date"],
    },
    "chargeback-analysis": {
        # Chargeback columns
        "chargeback_date": ["dispute date", "filing date", "CB date"],
        "chargeback_amount_cents": [
            "dispute amount",
            "CB amount",
            "chargeback value",
            "disputed amount",
        ],
        "chargeback_type": ["dispute type", "CB type", "fraud type"],
        "reason_code": ["dispute reason", "CB reason", "chargeback reason"],
        "chargeback_status": ["status", "dispute status", "resolution status"],
        "resolution_date": ["resolved date", "closure date"],
        # Transaction columns
        "transaction_amount_cents": ["original amount", "txn amount"],
        "transaction_date": ["original date", "purchase date"],
        # Merchant columns
        "merchant_name": ["merchant", "store", "shop", "vendor"],
        "mcc": ["category code", "MCC code"],
        "merchant_category": ["category", "merchant type", "business type"],
        "merchant_channel": ["merchant type", "store type"],
        "merchant_country": ["merchant location", "store country"],
    },
    "customer-cards": {
        # Card columns
        "card_type": ["form factor", "card form"],
        "card_network": ["network", "payment network", "brand"],
        "is_active": ["active", "active status", "card status"],
        "issue_date": ["issuance date", "card issue date"],
        "activation_date": ["activation", "first use date"],
        "campaign_code": ["promo code", "promotion", "campaign", "special edition"],
        # Customer columns
        "country": ["customer country", "region", "location"],
        "customer_type": ["account type", "client type"],
        "membership_tier": ["tier", "membership", "membership level", "plan"],
        "registration_date": ["signup date", "join date"],
    },
    "card-delivery": {
        "country": ["customer country", "delivery country", "region"],
        "card_type": ["form factor", "card form"],
        "order_type": ["order reason", "card order type"],
        "delivery_type": ["shipping type", "delivery speed", "shipping speed"],
        "issue_date": ["issuance date", "print date"],
        "delivery_date": ["arrival date", "receipt date", "delivered date"],
        "delivery_days": [
            "delivery time",
            "shipping time",
            "time to deliver",
            "days to deliver",
            "transit time",
        ],
    },
}

# =============================================================================
# CELL VALUE SYNONYMS FOR JOINED DATASETS
# =============================================================================

JOINED_CELL_VALUE_SYNONYMS: dict[str, dict[str, dict[str, list[str]]]] = {
    "spending-analysis": {
        "membership_tier": {
            "standard": ["std", "free account", "free tier", "basic"],
            "plus": ["plus tier", "plus plan"],
            "gold": ["gold tier", "gold plan"],
            "metal": ["metal tier", "premium", "metal plan"],
            "select": ["select tier", "select plan"],
        },
        "customer_type": {
            "personal": ["individual", "consumer", "retail customer", "private customer", "B2C", "Perso"],
            "business": ["corporate", "company", "B2B", "commercial", "SMB", "business account", "Biz"],
        },
        "is_approved": {
            "true": ["successful", "completed", "authorized", "accepted", "processed", "Presentment", "authorization"],
            "false": ["rejected", "failed", "denied", "unsuccessful", "blocked", "declined"],
        },
        "campaign_code": {
            "XMAS_2025": [
                "Christmas",
                "Xmas",
                "Christmas campaign",
                "holiday campaign",
                "Christmas special",
                "holiday edition",
            ],
        },
        "card_type": {
            "virtual": ["digital card", "virtual card", "digital-only"],
            "physical": ["plastic card", "physical card"],
        },
        "mcc": {
            "5411": ["groceries", "grocery stores", "supermarket", "food shopping"],
            "5541": ["gas stations", "petrol stations", "fuel", "gas", "filling station", "service station"],
            "5812": ["restaurants", "dining", "eating out", "restaurant spending", "food & beverage"],
            "5814": ["fast food", "quick service", "QSR", "fast casual", "takeaway", "takeout"],
            "3000": ["airlines", "flights", "air travel", "airline tickets", "flight purchases"],
            "7011": ["hotels", "accommodation", "lodging", "hotel bookings", "hospitality"],
            "4722": ["travel", "travel agencies", "vacation", "trips", "travel bookings"],
            "5912": ["pharmacies", "drugstore", "chemist", "pharmacy purchases"],
            "5311": ["department stores", "department store", "big-box retail", "general merchandise"],
            "5691": ["clothing stores", "apparel", "fashion", "clothes shopping", "clothing retail"],
            "5944": ["jewelry stores", "jewelry", "jewellery", "accessories", "watch stores"],
            "5945": ["toy stores", "toys", "games", "toy shops", "children's retail"],
            "5732": ["electronics", "electronics stores", "tech", "gadgets", "consumer electronics"],
            "5964": ["direct marketing", "e-commerce", "online retail", "direct sales"],
        },
    },
    "tokenization-analysis": {
        "wallet_type": {
            "apple_pay": ["Apple Pay", "Apple Wallet", "iOS Pay", "iPhone wallet", "Apple payment"],
            "google_pay": ["Google Pay", "GPay", "Google Wallet", "Android Pay", "Google payment"],
            "samsung_pay": ["Samsung Pay", "Samsung Wallet", "Samsung payment"],
            "garmin_pay": ["Garmin Wallet", "Runner wallet"],
        },
        "membership_tier": {
            "standard": ["std", "free account", "free tier"],
            "plus": ["plus tier"],
            "gold": ["gold tier"],
            "metal": ["metal tier", "premium"],
            "select": ["select tier"],
        },
        "customer_type": {
            "personal": ["individual", "consumer", "retail customer", "private customer", "B2C", "Perso"],
            "business": ["corporate", "company", "B2B", "commercial", "SMB", "business account", "Biz"],
        },
    },
    "chargeback-analysis": {
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
            "fraud_counterfeit": ["fake card", "cloned card", "counterfeit card", "skimmed card", "card cloning"],
            "fraud_lost_stolen": ["lost card", "stolen card", "missing card", "card theft"],
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
            "duplicate_charge": ["double charge", "charged twice", "duplicate transaction", "double billing", "Duplicate processing"],
            "incorrect_amount": [
                "wrong amount",
                "overcharge",
                "billing error",
                "amount mismatch",
                "Difference in amount",
                "unreasonable amount",
            ],
            "subscription_cancelled": ["cancelled subscription", "recurring charge after cancel", "unwanted renewal", "subscription dispute"],
        },
        "chargeback_status": {
            "pending": ["open", "in progress", "under review", "unresolved", "active dispute"],
            "won": ["User won", "refunded", "accepted", "merchant lost"],
            "lost": ["User lost", "not refunded", "rejected", "merchant won"],
            "expired": ["timed out", "closed", "expired dispute", "No response"],
        },
        "mcc": {
            "5411": ["groceries", "grocery stores", "supermarket", "food shopping"],
            "5541": ["gas stations", "petrol stations", "fuel", "gas", "filling station", "service station"],
            "5812": ["restaurants", "dining", "eating out", "restaurant spending", "food & beverage"],
            "5814": ["fast food", "quick service", "QSR", "fast casual", "takeaway", "takeout"],
            "3000": ["airlines", "flights", "air travel", "airline tickets", "flight purchases"],
            "7011": ["hotels", "accommodation", "lodging", "hotel bookings", "hospitality"],
            "4722": ["travel", "travel agencies", "vacation", "trips", "travel bookings"],
            "5912": ["pharmacies", "drugstore", "chemist", "pharmacy purchases"],
            "5311": ["department stores", "department store", "big-box retail", "general merchandise"],
            "5691": ["clothing stores", "apparel", "fashion", "clothes shopping", "clothing retail"],
            "5944": ["jewelry stores", "jewelry", "jewellery", "accessories", "watch stores"],
            "5945": ["toy stores", "toys", "games", "toy shops", "children's retail"],
            "5732": ["electronics", "electronics stores", "tech", "gadgets", "consumer electronics"],
            "5964": ["direct marketing", "e-commerce", "online retail", "direct sales"],
        },
    },
    "customer-cards": {
        "membership_tier": {
            "standard": ["std", "free account", "free tier"],
            "plus": ["plus tier"],
            "gold": ["gold tier"],
            "metal": ["metal tier", "premium"],
            "select": ["select tier"],
        },
        "customer_type": {
            "personal": ["individual", "consumer", "retail customer", "private customer", "B2C", "Perso"],
            "business": ["corporate", "company", "B2B", "commercial", "SMB", "business account", "Biz"],
        },
        "is_active": {
            "TRUE": ["active", "active cards", "current"],
            "FALSE": ["inactive", "cancelled", "closed"],
        },
        "card_type": {
            "virtual": ["digital card", "virtual card"],
            "physical": ["plastic card", "physical card"],
        },
    },
    "card-delivery": {
        "delivery_type": {
            "express": ["fast delivery", "priority shipping", "expedited", "rush delivery", "next-day", "quick delivery"],
            "standard": ["normal delivery", "regular shipping", "standard shipping", "economy delivery"],
        },
        "order_type": {
            "initial": ["first card", "Bundle card", "bundled card", "membership card"],
            "reorder": ["replacement", "re-issue", "new copy", "duplicate"],
            "replacement_expired": ["expired replacement", "renewal", "expiry replacement", "card renewal"],
            "additional": ["Non bundled", "extra card", "second card", "supplementary"],
        },
    },
}


# =============================================================================
# CUSTOM INSTRUCTIONS FOR OPTIMIZED Q TOPIC
# =============================================================================
# Compliance note: all data is synthetic. The schemas model EU personal data
# (names, email, date of birth) and payment card data (last four digits, transactions,
# chargebacks). If you adapt this sample to real data, you are responsible for GDPR,
# PCI DSS and any other applicable requirements.


OPTIMIZED_TOPIC_INSTRUCTIONS = """This topic contains pre-joined data for AnyCompany Bank's Cards domain analytics across 8 European countries (ES, DE, UK, FR, IT, NL, PL, PT).

DATASETS AND THEIR PURPOSE:

1. SPENDING ANALYSIS (spending-analysis)
   - Grain: One row per transaction
   - Contains: Transaction + Card + Customer + Merchant data
   - Use for: "What do metal tier customers spend on?", "XMAS campaign spending by category"
   - Key dimensions: membership_tier (standard/plus/gold/metal/select), campaign_code, merchant_category, mcc

2. TOKENIZATION ANALYSIS (tokenization-analysis)
   - Grain: One row per digital wallet provisioning event
   - Contains: Tokenization + Card + Customer data
   - Use for: "How long after joining do users tokenize?", "Tokenization timing by country"
   - Key metric: days_to_tokenize (AVERAGE by country)

3. CHARGEBACK ANALYSIS (chargeback-analysis)
   - Grain: One row per chargeback dispute
   - Contains: Chargeback + Transaction + Merchant data
   - Use for: "Why did chargebacks increase?", "Which merchants have fraud?"
   - Key dimensions: chargeback_type (unauthorized=fraud), merchant_name, reason_code

4. CUSTOMER CARDS (customer-cards)
   - Grain: One row per card
   - Contains: Card + Customer data
   - Use for: "How many cards per customer?", "Active cards by segment"
   - Filter: is_active = TRUE for counting active cards

5. CARD DELIVERY (card-delivery)
   - Grain: One row per physical card (virtual cards excluded)
   - Contains: Card delivery data with calculated delivery_days
   - Use for: "Which country has slowest delivery?", "Express vs standard delivery time"
   - Key metric: delivery_days (AVERAGE by country, delivery_type)

BUSINESS TERMS MAPPING:
- "premium" / "metal tier" = membership_tier = 'metal'
- "free account" / "std" = membership_tier = 'standard'
- "fraud" / "unauthorized" / "stolen card" = chargeback_type = 'unauthorized'
- "XMAS campaign" / "Christmas cards" / "holiday edition" = campaign_code = 'XMAS_2025'
- "online" / "e-commerce" = merchant_channel = 'ecom'
- "in-store" / "physical" = merchant_channel = 'pos'
- "ATM" / "cash machine" / "withdraw" = merchant_channel = 'atm'

AGGREGATION GUIDANCE:
- amount_cents, chargeback_amount_cents: Use SUM for totals, AVERAGE for typical values
- days_to_tokenize, delivery_days: Use AVERAGE for typical timing
- Count cards: Filter is_active = TRUE for "active cards"

AMOUNTS: All monetary values are stored in cents. Divide by 100 for euros/pounds display."""
