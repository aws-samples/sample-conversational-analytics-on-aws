# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Pre-joined QuickSight datasets for optimized Q Topic queries.

Compliance note: all data is synthetic. The schemas model EU personal data
(names, email, date of birth) and payment card data (last four digits, transactions,
chargebacks). If you adapt this sample to real data, you are responsible for GDPR,
PCI DSS and any other applicable requirements.

These datasets combine multiple tables via SQL JOINs to enable Q Topic
to answer cross-table questions that require data from multiple sources.

Each dataset is designed for specific use cases:
- spending-analysis: UC-3 (best customer spending), UC-5 (campaign success)
- tokenization-analysis: UC-1 (tokenization timing)
- chargeback-analysis: UC-2 (chargeback root cause)
- customer-cards: UC-6 (user profiling)
- card-delivery: UC-4 (delivery performance)
"""

from dataclasses import dataclass

from conversational_analytics.schema_definitions import QuickSightColumn


@dataclass
class JoinedDatasetDefinition:
    """Definition for a pre-joined QuickSight dataset using Custom SQL."""

    name: str  # e.g., "spending-analysis" (used in dataset ID)
    display_name: str  # e.g., "Spending Analysis" (shown in QuickSight)
    description: str  # Business context for Q Topic
    sql: str  # Athena SQL query with JOINs
    columns: list[QuickSightColumn]  # Column definitions for Q Topic
    grain: str  # What one row represents (for documentation)


# =============================================================================
# SQL QUERIES FOR PRE-JOINED DATASETS
# =============================================================================

SPENDING_ANALYSIS_SQL = """
SELECT
    -- Transaction (primary)
    t.transaction_id,
    t.amount_cents,
    t.currency,
    t.transaction_date,
    t.is_approved,
    -- Card
    ca.card_id,
    ca.card_type,
    ca.campaign_code,
    ca.is_active AS card_is_active,
    -- Customer
    c.customer_id,
    c.country AS customer_country,
    c.customer_type,
    c.membership_tier,
    -- Merchant
    m.merchant_id,
    m.merchant_name,
    m.merchant_category_code AS mcc,
    m.merchant_category_name AS merchant_category,
    m.channel AS merchant_channel,
    m.country AS merchant_country
FROM conversational_analytics.transactions t
JOIN conversational_analytics.cards ca ON t.card_id = ca.card_id
JOIN conversational_analytics.customers c ON ca.customer_id = c.customer_id
JOIN conversational_analytics.merchants m ON t.merchant_id = m.merchant_id
"""

TOKENIZATION_ANALYSIS_SQL = """
SELECT
    -- Tokenization (primary)
    tok.tokenization_id,
    tok.wallet_type,
    tok.tokenization_date,
    tok.days_to_tokenize,
    -- Card
    ca.card_id,
    ca.card_type,
    ca.issue_date AS card_issue_date,
    -- Customer
    c.customer_id,
    c.country,
    c.customer_type,
    c.membership_tier,
    c.registration_date
FROM conversational_analytics.tokenizations tok
JOIN conversational_analytics.cards ca ON tok.card_id = ca.card_id
JOIN conversational_analytics.customers c ON ca.customer_id = c.customer_id
"""

CHARGEBACK_ANALYSIS_SQL = """
SELECT
    -- Chargeback (primary)
    cb.chargeback_id,
    cb.chargeback_date,
    cb.chargeback_amount_cents,
    cb.chargeback_type,
    cb.reason_code,
    cb.status AS chargeback_status,
    cb.resolution_date,
    -- Transaction
    t.transaction_id,
    t.amount_cents AS transaction_amount_cents,
    t.transaction_date,
    t.card_id,
    -- Merchant
    m.merchant_id,
    m.merchant_name,
    m.merchant_category_code AS mcc,
    m.merchant_category_name AS merchant_category,
    m.channel AS merchant_channel,
    m.country AS merchant_country
FROM conversational_analytics.chargebacks cb
JOIN conversational_analytics.transactions t ON cb.transaction_id = t.transaction_id
JOIN conversational_analytics.merchants m ON t.merchant_id = m.merchant_id
"""

CUSTOMER_CARDS_SQL = """
SELECT
    -- Card (primary)
    ca.card_id,
    ca.card_type,
    ca.card_network,
    ca.is_active,
    ca.issue_date,
    ca.activation_date,
    ca.campaign_code,
    -- Customer
    c.customer_id,
    c.country,
    c.customer_type,
    c.membership_tier,
    c.registration_date
FROM conversational_analytics.cards ca
JOIN conversational_analytics.customers c ON ca.customer_id = c.customer_id
"""

CARD_DELIVERY_SQL = """
SELECT
    card_id,
    customer_id,
    country,
    card_type,
    order_type,
    delivery_type,
    issue_date,
    delivery_date,
    DATE_DIFF('day', issue_date, delivery_date) AS delivery_days
FROM conversational_analytics.cards
WHERE delivery_date IS NOT NULL
  AND issue_date IS NOT NULL
  AND card_type = 'physical'
"""


# =============================================================================
# COLUMN DEFINITIONS FOR EACH JOINED DATASET
# =============================================================================

SPENDING_ANALYSIS_COLUMNS = [
    # Transaction columns
    QuickSightColumn(
        "transaction_id",
        "STRING",
        "Unique identifier for each transaction",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "amount_cents",
        "INTEGER",
        "Transaction amount in cents. Divide by 100 for euros. Sum to get total spend.",
        is_dimension=False,
        semantic_type_name="Currency",
        default_aggregation="SUM",
        allowed_aggregations=["SUM", "AVERAGE", "MIN", "MAX", "COUNT"],
    ),
    QuickSightColumn(
        "currency",
        "STRING",
        "Currency code (EUR, GBP, PLN)",
    ),
    QuickSightColumn(
        "transaction_date",
        "DATE",
        "Date when the transaction occurred",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "is_approved",
        "BOOLEAN",
        "Whether the transaction was approved (TRUE) or declined (FALSE)",
    ),
    # Card columns
    QuickSightColumn(
        "card_id",
        "STRING",
        "Unique identifier for the card used",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "card_type",
        "STRING",
        "Card form factor: virtual (digital-only) or physical (plastic card)",
    ),
    QuickSightColumn(
        "campaign_code",
        "STRING",
        "Special card campaign code. XMAS_2025 = Christmas special edition cards.",
    ),
    QuickSightColumn(
        "card_is_active",
        "BOOLEAN",
        "Whether the card is currently active",
    ),
    # Customer columns
    QuickSightColumn(
        "customer_id",
        "STRING",
        "Unique identifier for the customer",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "customer_country",
        "STRING",
        "Customer's country of residence (ES=Spain, DE=Germany, UK, FR, IT, NL, PL, PT)",
    ),
    QuickSightColumn(
        "customer_type",
        "STRING",
        "Account type: personal (individuals) or business (companies/SMBs)",
    ),
    QuickSightColumn(
        "membership_tier",
        "STRING",
        "Membership level: standard (free), plus, gold, metal (premium), select",
    ),
    # Merchant columns
    QuickSightColumn(
        "merchant_id",
        "STRING",
        "Unique identifier for the merchant",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "merchant_name",
        "STRING",
        "Business name of the merchant where purchase was made",
    ),
    QuickSightColumn(
        "mcc",
        "STRING",
        "Merchant Category Code. Key codes: 4722=Travel, 5812=Restaurants, 5411=Groceries, 5541=Gas, 5944=Jewelry, 5945=Toys",
    ),
    QuickSightColumn(
        "merchant_category",
        "STRING",
        "Human-readable merchant category (e.g., 'Restaurants', 'Travel Agencies', 'Grocery Stores')",
    ),
    QuickSightColumn(
        "merchant_channel",
        "STRING",
        "Merchant's primary channel: pos (physical store), ecom (online), atm (ATM/cash withdrawal)",
    ),
    QuickSightColumn(
        "merchant_country",
        "STRING",
        "Country where the merchant is located",
    ),
]

TOKENIZATION_ANALYSIS_COLUMNS = [
    # Tokenization columns
    QuickSightColumn(
        "tokenization_id",
        "STRING",
        "Unique identifier for the tokenization event",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "wallet_type",
        "STRING",
        "Digital wallet provider: apple_pay, google_pay, samsung_pay, garmin_pay",
    ),
    QuickSightColumn(
        "tokenization_date",
        "DATE",
        "Date when the card was added to the digital wallet",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "days_to_tokenize",
        "INTEGER",
        "Days between customer registration and adding card to digital wallet. Average to see typical timing by country.",
        is_dimension=False,
        default_aggregation="AVERAGE",
        allowed_aggregations=["AVERAGE", "MIN", "MAX", "COUNT"],
    ),
    # Card columns
    QuickSightColumn(
        "card_id",
        "STRING",
        "Unique identifier for the tokenized card",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "card_type",
        "STRING",
        "Card form factor: virtual (digital-only) or physical (plastic card)",
    ),
    QuickSightColumn(
        "card_issue_date",
        "DATE",
        "Date when the card was issued",
        time_granularity="DAY",
    ),
    # Customer columns
    QuickSightColumn(
        "customer_id",
        "STRING",
        "Unique identifier for the customer",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "country",
        "STRING",
        "Customer's country (ES=Spain, DE=Germany, UK, FR)",
    ),
    QuickSightColumn(
        "customer_type",
        "STRING",
        "Account type: personal or business",
    ),
    QuickSightColumn(
        "membership_tier",
        "STRING",
        "Membership level: standard, plus, gold, metal, select",
    ),
    QuickSightColumn(
        "registration_date",
        "DATE",
        "When the customer completed KYC and joined AnyCompany Bank. Start date for days_to_tokenize calculation.",
        time_granularity="DAY",
    ),
]

CHARGEBACK_ANALYSIS_COLUMNS = [
    # Chargeback columns
    QuickSightColumn(
        "chargeback_id",
        "STRING",
        "Unique identifier for the chargeback dispute",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "chargeback_date",
        "DATE",
        "Date when the chargeback was filed. Look for spikes in specific weeks.",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "chargeback_amount_cents",
        "INTEGER",
        "Disputed amount in cents. Sum to get total chargeback value.",
        is_dimension=False,
        semantic_type_name="Currency",
        default_aggregation="SUM",
        allowed_aggregations=["SUM", "AVERAGE", "MIN", "MAX", "COUNT"],
    ),
    QuickSightColumn(
        "chargeback_type",
        "STRING",
        "Type of dispute: 'unauthorized' (fraud - cardholder didn't authorize, also called 'fraud') or 'authorized' (merchandise/service issues)",
    ),
    QuickSightColumn(
        "reason_code",
        "STRING",
        "Detailed reason: fraud_card_not_present, merchandise_not_received, duplicate_charge, subscription_cancelled, other",
    ),
    QuickSightColumn(
        "chargeback_status",
        "STRING",
        "Current status: open, resolved_merchant_favor, resolved_customer_favor",
    ),
    QuickSightColumn(
        "resolution_date",
        "DATE",
        "Date when the chargeback was resolved (if resolved)",
        time_granularity="DAY",
    ),
    # Transaction columns
    QuickSightColumn(
        "transaction_id",
        "STRING",
        "Unique identifier for the original transaction",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "transaction_amount_cents",
        "INTEGER",
        "Original transaction amount in cents",
        is_dimension=False,
        semantic_type_name="Currency",
        default_aggregation="SUM",
        allowed_aggregations=["SUM", "AVERAGE", "MIN", "MAX", "COUNT"],
    ),
    QuickSightColumn(
        "transaction_date",
        "DATE",
        "Date of the original transaction",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "card_id",
        "STRING",
        "Card used in the disputed transaction",
        disable_indexing=True,
    ),
    # Merchant columns
    QuickSightColumn(
        "merchant_id",
        "STRING",
        "Unique identifier for the merchant",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "merchant_name",
        "STRING",
        "Business name of the merchant involved in the chargeback",
    ),
    QuickSightColumn(
        "mcc",
        "STRING",
        "Merchant Category Code for the disputed transaction",
    ),
    QuickSightColumn(
        "merchant_category",
        "STRING",
        "Human-readable merchant category",
    ),
    QuickSightColumn(
        "merchant_channel",
        "STRING",
        "Merchant's primary channel: pos (physical store), ecom (online), atm (ATM/cash withdrawal)",
    ),
    QuickSightColumn(
        "merchant_country",
        "STRING",
        "Country where the merchant is located",
    ),
]

CUSTOMER_CARDS_COLUMNS = [
    # Card columns (primary)
    QuickSightColumn(
        "card_id",
        "STRING",
        "Unique identifier for the card",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "card_type",
        "STRING",
        "Card form factor: virtual (digital-only) or physical (plastic card)",
    ),
    QuickSightColumn(
        "card_network",
        "STRING",
        "Card network: mastercard",
    ),
    QuickSightColumn(
        "is_active",
        "BOOLEAN",
        "Whether the card is currently active. Filter to TRUE when counting 'active cards' per customer.",
    ),
    QuickSightColumn(
        "issue_date",
        "DATE",
        "Date when the card was issued",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "activation_date",
        "DATE",
        "Date when the card was activated (first use or explicit activation)",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "campaign_code",
        "STRING",
        "Special card campaign code (e.g., XMAS_2025 for Christmas edition)",
    ),
    # Customer columns
    QuickSightColumn(
        "customer_id",
        "STRING",
        "Unique identifier for the customer who owns this card",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "country",
        "STRING",
        "Customer's country (ES=Spain, DE=Germany, UK, FR, IT, NL, PL, PT)",
    ),
    QuickSightColumn(
        "customer_type",
        "STRING",
        "Account type: personal (individuals) or business (companies/SMBs)",
    ),
    QuickSightColumn(
        "membership_tier",
        "STRING",
        "Membership level: standard, plus, gold, metal, select",
    ),
    QuickSightColumn(
        "registration_date",
        "DATE",
        "When the customer joined AnyCompany Bank",
        time_granularity="DAY",
    ),
]

CARD_DELIVERY_COLUMNS = [
    QuickSightColumn(
        "card_id",
        "STRING",
        "Unique identifier for the card",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "customer_id",
        "STRING",
        "Unique identifier for the customer",
        disable_indexing=True,
    ),
    QuickSightColumn(
        "country",
        "STRING",
        "Country where card was delivered (ES=Spain, DE=Germany, UK, FR)",
    ),
    QuickSightColumn(
        "card_type",
        "STRING",
        "Card form factor: always 'physical' in this dataset (virtual cards excluded)",
    ),
    QuickSightColumn(
        "order_type",
        "STRING",
        "Type of card order: initial, reorder, replacement_expired, additional",
    ),
    QuickSightColumn(
        "delivery_type",
        "STRING",
        "Shipping speed: express or standard. Express is faster but costs more.",
    ),
    QuickSightColumn(
        "issue_date",
        "DATE",
        "Date when the card was issued/printed",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "delivery_date",
        "DATE",
        "Date when the card was delivered to the customer",
        time_granularity="DAY",
    ),
    QuickSightColumn(
        "delivery_days",
        "INTEGER",
        "Days from card issue to delivery. Average to see typical delivery time by country and delivery type.",
        is_dimension=False,
        default_aggregation="AVERAGE",
        allowed_aggregations=["AVERAGE", "MIN", "MAX", "COUNT"],
    ),
]


# =============================================================================
# JOINED DATASETS DICTIONARY
# =============================================================================

JOINED_DATASETS: dict[str, JoinedDatasetDefinition] = {
    "spending-analysis": JoinedDatasetDefinition(
        name="spending-analysis",
        display_name="Spending Analysis",
        description="Transaction-level data with customer, card, and merchant context. Use for analyzing spending patterns by customer segment, campaign success, and merchant preferences.",
        sql=SPENDING_ANALYSIS_SQL,
        columns=SPENDING_ANALYSIS_COLUMNS,
        grain="transaction",
    ),
    "tokenization-analysis": JoinedDatasetDefinition(
        name="tokenization-analysis",
        display_name="Tokenization Analysis",
        description="Digital wallet adoption data with customer context. Use for analyzing how long after joining customers add cards to Apple Pay, Google Pay, or Samsung Pay.",
        sql=TOKENIZATION_ANALYSIS_SQL,
        columns=TOKENIZATION_ANALYSIS_COLUMNS,
        grain="tokenization_event",
    ),
    "chargeback-analysis": JoinedDatasetDefinition(
        name="chargeback-analysis",
        display_name="Chargeback Analysis",
        description="Chargeback disputes with transaction and merchant details. Use for root cause analysis of fraud patterns and chargeback spikes.",
        sql=CHARGEBACK_ANALYSIS_SQL,
        columns=CHARGEBACK_ANALYSIS_COLUMNS,
        grain="chargeback",
    ),
    "customer-cards": JoinedDatasetDefinition(
        name="customer-cards",
        display_name="Customer Cards",
        description="Card portfolio data by customer. Use for analyzing cards per customer, card ownership patterns by segment and membership type.",
        sql=CUSTOMER_CARDS_SQL,
        columns=CUSTOMER_CARDS_COLUMNS,
        grain="card",
    ),
    "card-delivery": JoinedDatasetDefinition(
        name="card-delivery",
        display_name="Card Delivery",
        description="Physical card delivery performance. Use for analyzing delivery times by country and delivery type. Virtual cards are excluded.",
        sql=CARD_DELIVERY_SQL,
        columns=CARD_DELIVERY_COLUMNS,
        grain="physical_card",
    ),
}
