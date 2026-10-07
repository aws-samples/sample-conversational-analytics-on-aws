# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Schema definitions for Conversational Analytics tables.

This module is the single source of truth for all table schemas, column types,
and QuickSight configurations. Changes here cascade to:
- generators (data generation)
- CDK stacks (infrastructure)
- QuickSight constructs (DataSets, Q Topics)
- Athena DDL (table creation)

Compliance note: all data is synthetic. The schemas model EU personal data
(names, email, date of birth) and payment card data (last four digits, transactions,
chargebacks). If you adapt this sample to real data, you are responsible for GDPR,
PCI DSS and any other applicable requirements.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

# =============================================================================
# ENUMS
# =============================================================================


class Country(str, Enum):
    """ISO 3166-1 alpha-2 country codes for supported countries."""

    ES = "ES"  # Spain
    DE = "DE"  # Germany
    UK = "UK"  # United Kingdom
    FR = "FR"  # France
    IT = "IT"  # Italy
    NL = "NL"  # Netherlands
    PL = "PL"  # Poland
    PT = "PT"  # Portugal


class CardType(str, Enum):
    """Card product types."""

    VIRTUAL = "virtual"
    PHYSICAL = "physical"


class CustomerType(str, Enum):
    """Customer profile types."""

    PERSONAL = "personal"
    BUSINESS = "business"


class MembershipTier(str, Enum):
    """Customer membership tier levels."""

    STANDARD = "standard"
    PLUS = "plus"
    GOLD = "gold"
    METAL = "metal"
    SELECT = "select"


class WalletType(str, Enum):
    """Digital wallet types for tokenization."""

    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    SAMSUNG_PAY = "samsung_pay"
    GARMIN_PAY = "garmin_pay"


class MerchantChannel(str, Enum):
    """Merchant transaction channel."""

    POS = "pos"  # Point of Sale (in-store)
    ECOM = "ecom"  # E-commerce (online)
    ATM = "atm"  # ATM / Cash withdrawal


class ChargebackType(str, Enum):
    """Chargeback classification type."""

    UNAUTHORIZED = "unauthorized"  # Fraud-related
    AUTHORIZED = "authorized"  # Dispute over legitimate transaction


class DeliveryType(str, Enum):
    """Card delivery speed type."""

    EXPRESS = "express"
    STANDARD = "standard"


class OrderType(str, Enum):
    """Card order type."""

    INITIAL = "initial"
    REORDER = "reorder"
    REPLACEMENT_EXPIRED = "replacement_expired"
    ADDITIONAL = "additional"  # Extra card for same customer


class UserStatus(str, Enum):
    """Customer activity status."""

    ACTIVE = "active"  # MAU - Monthly Active User
    DORMANT = "dormant"  # Inactive 90+ days


class ChargebackReasonCode(str, Enum):
    """Chargeback reason codes."""

    # Unauthorized (fraud) codes
    FRAUD_CARD_NOT_PRESENT = "fraud_card_not_present"
    FRAUD_COUNTERFEIT = "fraud_counterfeit"
    FRAUD_LOST_STOLEN = "fraud_lost_stolen"

    # Authorized (dispute) codes
    MERCHANDISE_NOT_RECEIVED = "merchandise_not_received"
    MERCHANDISE_DEFECTIVE = "merchandise_defective"
    DUPLICATE_CHARGE = "duplicate_charge"
    INCORRECT_AMOUNT = "incorrect_amount"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    OTHER = "other"


class ChargebackStatus(str, Enum):
    """Chargeback resolution status."""

    PENDING = "pending"
    WON = "won"  # Decided in cardholder's favor (customer won)
    LOST = "lost"  # Decided against cardholder (merchant won)
    EXPIRED = "expired"


# =============================================================================
# COUNTRY DISTRIBUTIONS
# =============================================================================

# Distribution of customers across countries (must sum to 1.0)
COUNTRY_DISTRIBUTION: dict[Country, float] = {
    Country.ES: 0.25,  # Spain - primary market
    Country.DE: 0.20,  # Germany
    Country.UK: 0.15,  # United Kingdom
    Country.FR: 0.12,  # France
    Country.IT: 0.10,  # Italy
    Country.NL: 0.07,  # Netherlands
    Country.PL: 0.06,  # Poland
    Country.PT: 0.05,  # Portugal
}


# =============================================================================
# TABLE DATACLASSES
# =============================================================================


@dataclass
class Customer:
    """Customer table schema."""

    customer_id: str  # C_000001
    email: str
    first_name: str
    last_name: str
    date_of_birth: date
    country: str  # ISO 3166-1 alpha-2
    customer_type: str  # personal | business
    membership_tier: str  # standard | plus | gold | metal | select
    registration_date: date
    user_status: str  # active | dormant
    created_at: datetime


@dataclass
class Card:
    """Card table schema."""

    card_id: str  # CARD_000001
    customer_id: str  # FK to customers
    card_type: str  # virtual | physical
    card_network: str  # mastercard
    last_four_digits: str
    expiry_date: date
    issue_date: date
    delivery_date: date | None
    delivery_type: str  # express | standard
    order_type: str  # initial | reorder | replacement_expired
    activation_date: date | None
    country: str  # Partitioning
    year: int  # Partitioning
    month: int  # Partitioning
    campaign_code: str | None  # e.g., XMAS_2025
    is_active: bool
    created_at: datetime


@dataclass
class Merchant:
    """Merchant table schema."""

    merchant_id: str  # M_000001 or M_FASTSHOP_001
    merchant_name: str
    merchant_category_code: str  # MCC 4-digit code
    merchant_category_name: str
    channel: str  # pos | ecom | atm
    country: str
    city: str | None
    created_at: datetime


@dataclass
class Transaction:
    """Transaction table schema."""

    transaction_id: str  # TXN_000000001
    card_id: str  # FK to cards
    merchant_id: str  # FK to merchants
    amount_cents: int  # Amount in cents to avoid float issues
    currency: str  # ISO 4217 (EUR, GBP, etc.)
    transaction_date: datetime
    authorization_code: str
    is_approved: bool
    decline_reason: str | None
    country: str  # Partitioning
    year: int  # Partitioning
    month: int  # Partitioning


@dataclass
class Tokenization:
    """Tokenization table schema - tracks digital wallet provisioning."""

    tokenization_id: str  # TOK_000001
    card_id: str  # FK to cards
    wallet_type: str  # apple_pay | google_pay | samsung_pay | garmin_pay
    token_requestor_id: str
    tokenization_date: datetime
    customer_registration_date: date  # Denormalized for analysis
    days_to_tokenize: int  # Calculated: tokenization_date - registration_date


@dataclass
class Chargeback:
    """Chargeback table schema - core for UC-2 analysis."""

    chargeback_id: str  # CB_000001
    transaction_id: str  # FK to transactions
    card_id: str  # FK to cards (denormalized)
    merchant_id: str  # FK to merchants (denormalized)
    chargeback_date: date
    chargeback_amount_cents: int
    currency: str
    chargeback_type: str  # unauthorized | authorized
    reason_code: str  # fraud_card_not_present, etc.
    status: str  # pending | won | lost | expired
    resolution_date: date | None
    year: int  # Partitioning
    month: int  # Partitioning


# =============================================================================
# TABLE METADATA
# =============================================================================

# List of all table names (used by upload.py, validate.py)
TABLES: list[str] = [
    "merchants",
    "customers",
    "cards",
    "transactions",
    "tokenizations",
    "chargebacks",
]

# Table generation order (respects foreign key dependencies)
TABLE_GENERATION_ORDER: list[str] = [
    "merchants",  # No dependencies
    "customers",  # No dependencies
    "cards",  # Depends on customers
    "transactions",  # Depends on cards, merchants
    "tokenizations",  # Depends on cards
    "chargebacks",  # Depends on transactions, cards, merchants
]

# =============================================================================
# DATA TIERS (S, M, L)
# =============================================================================
# S (Small): Fast iteration, end-to-end testing (~30 seconds)
# M (Medium): Realistic testing (~5 minutes)
# L (Large): Production-like, full dataset (~30+ minutes)


class DataTier(str, Enum):
    """Data generation tier sizes."""

    S = "S"  # Small - rapid iteration
    M = "M"  # Medium - realistic testing
    L = "L"  # Large - production-like


# Row counts per tier
TABLE_ROW_COUNTS_BY_TIER: dict[DataTier, dict[str, int]] = {
    DataTier.S: {
        "merchants": 100,
        "customers": 1_000,
        "cards": 1_200,  # approximate: derived from the customer mix (UC-6)
        "transactions": 50_000,
        "tokenizations": 700,  # ~60% of active cards
        "chargebacks": 250,
    },
    DataTier.M: {
        "merchants": 1_000,
        "customers": 10_000,
        "cards": 12_000,  # approximate: derived from the customer mix (UC-6)
        "transactions": 500_000,
        "tokenizations": 7_000,  # ~60% of active cards
        "chargebacks": 2_500,
    },
    DataTier.L: {
        "merchants": 10_000,
        "customers": 100_000,
        "cards": 120_000,  # approximate: derived from the customer mix (UC-6)
        "transactions": 5_000_000,
        "tokenizations": 70_000,  # ~60% of active cards
        "chargebacks": 25_000,
    },
}

# Default tier
DEFAULT_TIER = DataTier.S

# Legacy alias for backward compatibility
TABLE_ROW_COUNTS: dict[str, int] = TABLE_ROW_COUNTS_BY_TIER[DataTier.L]


def get_row_counts(tier: DataTier = DEFAULT_TIER) -> dict[str, int]:
    """Get row counts for a specific tier."""
    return TABLE_ROW_COUNTS_BY_TIER[tier]

# Partitioning keys per table
TABLE_PARTITIONS: dict[str, list[str]] = {
    "merchants": [],
    "customers": ["country"],
    "cards": ["country", "year", "month"],
    "transactions": ["country", "year", "month"],
    "tokenizations": ["wallet_type"],
    "chargebacks": ["year", "month"],
}


# =============================================================================
# QUICKSIGHT COLUMN DEFINITIONS
# =============================================================================

# QuickSight InputColumn types: STRING, INTEGER, DECIMAL, DATETIME, BIT, BOOLEAN, JSON


@dataclass
class QuickSightColumn:
    """QuickSight column definition for DataSet and Q Topic creation.

    Enhanced with Q Topic configuration options:
    - semantic_type_name: E.g., "Currency", "Boolean", "Date", "ID"
    - time_granularity: For date/datetime fields: DAY, WEEK, MONTH, QUARTER, YEAR
    - default_aggregation: Default aggregation for measures: SUM, COUNT, AVERAGE, etc.
    - allowed_aggregations: List of allowed aggregations (if restricted)
    - disable_indexing: Hide from autocomplete (useful for internal IDs)
    """

    name: str
    qs_type: str  # QuickSight type: STRING, INTEGER, DECIMAL, DATETIME, BOOLEAN
    description: str = ""
    is_dimension: bool = True  # False = measure
    semantic_type: str | None = None  # Legacy - use semantic_type_name instead
    non_additive: bool = False  # For Q Topics: rates/ratios that shouldn't be summed
    # Enhanced Q Topic configuration
    semantic_type_name: str | None = None  # TypeName for SemanticType
    time_granularity: str | None = None  # SECOND, MINUTE, HOUR, DAY, WEEK, MONTH, QUARTER, YEAR
    default_aggregation: str | None = None  # SUM, COUNT, AVERAGE, MIN, MAX, etc.
    allowed_aggregations: list[str] | None = None  # Restrict allowed aggregations
    disable_indexing: bool = False  # Hide from autocomplete


# QuickSight table definitions with enhanced column metadata for Q Topics
# Descriptions are business-focused to help Q understand context
QUICKSIGHT_TABLES: dict[str, list[QuickSightColumn]] = {
    "merchants": [
        QuickSightColumn(
            "merchant_id", "STRING",
            "Unique identifier for each merchant/store where transactions occur",
            disable_indexing=True  # Internal ID, not useful for NL queries
        ),
        QuickSightColumn(
            "merchant_name", "STRING",
            "Business name of the merchant. Use to find transactions at specific stores like 'FastShop Online'"
        ),
        QuickSightColumn(
            "merchant_category_code", "STRING",
            "4-digit MCC code classifying the merchant's industry (e.g., 5411 for groceries, 5812 for restaurants)"
        ),
        QuickSightColumn(
            "merchant_category_name", "STRING",
            "Human-readable merchant category (e.g., 'Grocery Stores', 'Restaurants', 'Airlines')"
        ),
        QuickSightColumn(
            "channel", "STRING",
            "How transactions occur: 'pos' (in-store), 'ecom' (online), 'atm' (ATM/cash withdrawal)"
        ),
        QuickSightColumn(
            "country", "STRING",
            "Country where the merchant is located (ISO 2-letter code: ES, DE, UK, FR, IT, NL, PL, PT)"
        ),
        QuickSightColumn("city", "STRING", "City where the merchant is located"),
        QuickSightColumn("created_at", "DATETIME", "When the merchant record was created", disable_indexing=True),
    ],
    "customers": [
        QuickSightColumn(
            "customer_id", "STRING",
            "Unique identifier for each customer/cardholder",
            disable_indexing=True
        ),
        QuickSightColumn("email", "STRING", "Customer's email address", disable_indexing=True),
        QuickSightColumn("first_name", "STRING", "Customer's first name", disable_indexing=True),
        QuickSightColumn("last_name", "STRING", "Customer's last name", disable_indexing=True),
        QuickSightColumn(
            "date_of_birth", "DATE",
            "Customer's birth date for age analysis",
            time_granularity="YEAR"
        ),
        QuickSightColumn(
            "country", "STRING",
            "Customer's country of residence (ISO 2-letter: ES, DE, UK, FR, IT, NL, PL, PT)"
        ),
        QuickSightColumn(
            "customer_type", "STRING",
            "Account type: 'personal' for individuals, 'business' for companies/SMBs"
        ),
        QuickSightColumn(
            "membership_tier", "STRING",
            "Membership level: 'standard' (free), 'plus', 'gold', 'metal' (premium), 'select'"
        ),
        QuickSightColumn(
            "registration_date", "DATE",
            "When the customer registered/joined AnyCompany Bank. Use to calculate time-to-tokenize",
            time_granularity="DAY"
        ),
        QuickSightColumn(
            "user_status", "STRING",
            "Activity status: 'active' (used card in last 90 days) or 'dormant' (inactive)"
        ),
        QuickSightColumn("created_at", "DATETIME", "Record creation timestamp", disable_indexing=True),
    ],
    "cards": [
        QuickSightColumn(
            "card_id", "STRING",
            "Unique identifier for each card product issued",
            disable_indexing=True
        ),
        QuickSightColumn(
            "customer_id", "STRING",
            "Links to the customer who owns this card",
            disable_indexing=True
        ),
        QuickSightColumn(
            "card_type", "STRING",
            "Card form factor: 'virtual' (digital-only) or 'physical' (plastic card)"
        ),
        QuickSightColumn(
            "card_network", "STRING",
            "Payment network: 'mastercard'"
        ),
        QuickSightColumn("last_four_digits", "STRING", "Last 4 digits of card number", disable_indexing=True),
        QuickSightColumn(
            "expiry_date", "DATE",
            "When the card expires",
            time_granularity="MONTH"
        ),
        QuickSightColumn(
            "issue_date", "DATE",
            "When the card was issued/manufactured",
            time_granularity="DAY"
        ),
        QuickSightColumn(
            "delivery_date", "DATE",
            "When the physical card was delivered to customer",
            time_granularity="DAY"
        ),
        QuickSightColumn(
            "delivery_type", "STRING",
            "Shipping speed: 'express' (fast, 3-5 days) or 'standard' (regular, 7-15 days)"
        ),
        QuickSightColumn(
            "order_type", "STRING",
            "Why card was ordered: 'initial' (first card), 'reorder' (replacement), 'replacement_expired' (renewal)"
        ),
        QuickSightColumn(
            "activation_date", "DATE",
            "When customer first used/activated the card. Use with issue_date to calculate delivery time",
            time_granularity="DAY"
        ),
        QuickSightColumn(
            "country", "STRING",
            "Country where card was issued (ISO 2-letter: ES, DE, UK, FR, IT, NL, PL, PT)"
        ),
        QuickSightColumn("year", "INTEGER", "Year card was issued (partition key)", disable_indexing=True),
        QuickSightColumn("month", "INTEGER", "Month card was issued (partition key)", disable_indexing=True),
        QuickSightColumn(
            "campaign_code", "STRING",
            "Marketing campaign code if special edition card (e.g., 'XMAS_2025' for Christmas special)"
        ),
        QuickSightColumn(
            "is_active", "BOOLEAN",
            "Whether the card is currently active and usable"
        ),
        QuickSightColumn("created_at", "DATETIME", "Record creation timestamp", disable_indexing=True),
    ],
    "transactions": [
        QuickSightColumn(
            "transaction_id", "STRING",
            "Unique identifier for each card transaction",
            disable_indexing=True
        ),
        QuickSightColumn(
            "card_id", "STRING",
            "Links to the card used for this transaction",
            disable_indexing=True
        ),
        QuickSightColumn(
            "merchant_id", "STRING",
            "Links to the merchant where transaction occurred",
            disable_indexing=True
        ),
        QuickSightColumn(
            "amount_cents", "INTEGER",
            "Transaction amount in cents (divide by 100 for euros). Sum to get total spend",
            is_dimension=False,
            semantic_type_name="Currency",
            default_aggregation="SUM",
            allowed_aggregations=["SUM", "AVERAGE", "MIN", "MAX", "COUNT"]
        ),
        QuickSightColumn(
            "currency", "STRING",
            "Transaction currency (ISO 4217: EUR, GBP, PLN)"
        ),
        QuickSightColumn(
            "transaction_date", "DATETIME",
            "When the transaction occurred. Use for time-series analysis",
            time_granularity="DAY"
        ),
        QuickSightColumn("authorization_code", "STRING", "Bank authorization code", disable_indexing=True),
        QuickSightColumn(
            "is_approved", "BOOLEAN",
            "Whether transaction was approved (true) or declined (false)"
        ),
        QuickSightColumn(
            "decline_reason", "STRING",
            "Why transaction was declined (only populated if is_approved=false)"
        ),
        QuickSightColumn(
            "country", "STRING",
            "Country where transaction occurred (ISO 2-letter: ES, DE, UK, FR, IT, NL, PL, PT)"
        ),
        QuickSightColumn("year", "INTEGER", "Transaction year (partition key)", disable_indexing=True),
        QuickSightColumn("month", "INTEGER", "Transaction month (partition key)", disable_indexing=True),
    ],
    "tokenizations": [
        QuickSightColumn(
            "tokenization_id", "STRING",
            "Unique identifier for each digital wallet provisioning event",
            disable_indexing=True
        ),
        QuickSightColumn(
            "card_id", "STRING",
            "Links to the card that was added to digital wallet",
            disable_indexing=True
        ),
        QuickSightColumn(
            "wallet_type", "STRING",
            "Digital wallet provider: 'apple_pay', 'google_pay', 'samsung_pay', or 'garmin_pay'"
        ),
        QuickSightColumn("token_requestor_id", "STRING", "Token requestor identifier", disable_indexing=True),
        QuickSightColumn(
            "tokenization_date", "DATETIME",
            "When the card was added to the digital wallet",
            time_granularity="DAY"
        ),
        QuickSightColumn(
            "customer_registration_date", "DATE",
            "When the customer originally registered (for calculating days_to_tokenize)",
            time_granularity="DAY"
        ),
        QuickSightColumn(
            "days_to_tokenize", "INTEGER",
            "Days between customer registration and adding card to digital wallet. Key metric for tokenization timing analysis - lower is better",
            is_dimension=False,
            default_aggregation="AVERAGE",
            allowed_aggregations=["AVERAGE", "MEDIAN", "MIN", "MAX", "COUNT"]
        ),
    ],
    "chargebacks": [
        QuickSightColumn(
            "chargeback_id", "STRING",
            "Unique identifier for each chargeback/dispute",
            disable_indexing=True
        ),
        QuickSightColumn(
            "transaction_id", "STRING",
            "Links to the original transaction being disputed",
            disable_indexing=True
        ),
        QuickSightColumn(
            "card_id", "STRING",
            "Links to the card involved in the dispute",
            disable_indexing=True
        ),
        QuickSightColumn(
            "merchant_id", "STRING",
            "Links to the merchant involved in the dispute. Use to find problematic merchants",
            disable_indexing=True
        ),
        QuickSightColumn(
            "chargeback_date", "DATE",
            "When the chargeback was filed. Use for time-series analysis of dispute trends",
            time_granularity="DAY"
        ),
        QuickSightColumn(
            "chargeback_amount_cents", "INTEGER",
            "Disputed amount in cents (divide by 100 for euros). Sum to get total chargeback value",
            is_dimension=False,
            semantic_type_name="Currency",
            default_aggregation="SUM",
            allowed_aggregations=["SUM", "AVERAGE", "MIN", "MAX", "COUNT"]
        ),
        QuickSightColumn(
            "currency", "STRING",
            "Chargeback currency (ISO 4217: EUR, GBP, PLN)"
        ),
        QuickSightColumn(
            "chargeback_type", "STRING",
            "Dispute classification: 'unauthorized' (fraud - customer didn't authorize) or 'authorized' (non-fraud disputes like merchandise issues)"
        ),
        QuickSightColumn(
            "reason_code", "STRING",
            "Specific reason: fraud_card_not_present, fraud_counterfeit, merchandise_not_received, duplicate_charge, subscription_cancelled, etc."
        ),
        QuickSightColumn(
            "status", "STRING",
            "Resolution status: 'pending' (open), 'won' (merchant won), 'lost' (customer won), 'expired'"
        ),
        QuickSightColumn(
            "resolution_date", "DATE",
            "When the dispute was resolved (null if still pending)",
            time_granularity="DAY"
        ),
        QuickSightColumn("year", "INTEGER", "Chargeback year (partition key)", disable_indexing=True),
        QuickSightColumn("month", "INTEGER", "Chargeback month (partition key)", disable_indexing=True),
    ],
}


# =============================================================================
# GLUE/ATHENA TYPE MAPPING
# =============================================================================

# Python type to Glue/Athena type mapping
ATHENA_TYPE_MAPPING: dict[str, str] = {
    "str": "string",
    "int": "bigint",
    "float": "double",
    "bool": "boolean",
    "date": "date",
    "datetime": "timestamp",
}

# QuickSight to Athena type mapping
# Note: QuickSight uses DATETIME for both dates and timestamps,
# but Athena/Parquet distinguishes between date and timestamp.
# We use DATETIME for timestamps and DATE for date-only columns.
QS_TO_ATHENA_TYPE: dict[str, str] = {
    "STRING": "string",
    "INTEGER": "bigint",
    "DECIMAL": "double",
    "DATETIME": "timestamp",
    "DATE": "date",  # For date-only columns (no time component)
    "BOOLEAN": "boolean",
}


# =============================================================================
# MERCHANT CATEGORY CODES (MCC)
# =============================================================================

# Common MCCs for transaction generation
MCC_CATEGORIES: dict[str, tuple[str, str]] = {
    # (MCC code, category name)
    "5411": ("5411", "Grocery Stores"),
    "5541": ("5541", "Gas Stations"),
    "5812": ("5812", "Restaurants"),
    "5814": ("5814", "Fast Food"),
    "4111": ("4111", "Transportation"),
    "3000": ("3000", "Airlines"),
    "7011": ("7011", "Hotels"),
    "5912": ("5912", "Pharmacies"),
    "5311": ("5311", "Department Stores"),
    "5691": ("5691", "Clothing Stores"),
    "5944": ("5944", "Jewelry Stores"),
    "5945": ("5945", "Toy Stores"),
    "5732": ("5732", "Electronics"),
    "5999": ("5999", "Miscellaneous Retail"),
    "5964": ("5964", "Direct Marketing"),  # E-commerce
}

# MCC distribution for regular vs metal tier customers
MCC_DISTRIBUTION_REGULAR: dict[str, float] = {
    "5411": 0.25,  # Groceries - most common
    "5541": 0.20,  # Gas
    "5812": 0.10,  # Restaurants
    "5814": 0.10,  # Fast food
    "5311": 0.08,  # Department stores
    "5912": 0.07,  # Pharmacies
    "5732": 0.05,  # Electronics
    "5999": 0.15,  # Misc retail
}

MCC_DISTRIBUTION_METAL: dict[str, float] = {
    "3000": 0.15,  # Airlines - metal tier travels more
    "7011": 0.15,  # Hotels
    "5812": 0.26,  # Restaurants (upscale)
    "5944": 0.04,  # Jewelry
    "5691": 0.10,  # Clothing
    "5311": 0.10,  # Department stores
    "5732": 0.10,  # Electronics
    "5999": 0.10,  # Misc
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_table_columns(table_name: str) -> list[str]:
    """Get column names for a table from QuickSight definitions."""
    if table_name not in QUICKSIGHT_TABLES:
        raise ValueError(f"Unknown table: {table_name}")
    return [col.name for col in QUICKSIGHT_TABLES[table_name]]


def get_partition_columns(table_name: str) -> list[str]:
    """Get partition column names for a table."""
    return TABLE_PARTITIONS.get(table_name, [])


def get_non_partition_columns(table_name: str) -> list[str]:
    """Get non-partition column names for a table."""
    all_cols = get_table_columns(table_name)
    partition_cols = get_partition_columns(table_name)
    return [c for c in all_cols if c not in partition_cols]
