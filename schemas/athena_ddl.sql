-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
-- SPDX-License-Identifier: MIT-0

-- Conversational Analytics Athena DDL Statements
-- These statements create external tables pointing to Parquet files in S3.
-- Run via scripts/create_tables.py after uploading data to S3.
--
-- IMPORTANT: The S3_BUCKET placeholder will be replaced at runtime.
--
-- Compliance note: all data is synthetic. The schemas model EU personal data
-- (names, email, date of birth) and payment card data (last four digits, transactions,
-- chargebacks). If you adapt this sample to real data, you are responsible for GDPR,
-- PCI DSS and any other applicable requirements.

-- =============================================================================
-- MERCHANTS TABLE (no partitioning)
-- =============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS conversational_analytics.merchants (
    merchant_id STRING COMMENT 'Unique merchant identifier',
    merchant_name STRING COMMENT 'Business name',
    merchant_category_code STRING COMMENT 'MCC code',
    merchant_category_name STRING COMMENT 'MCC description',
    channel STRING COMMENT 'Transaction channel: pos, ecom, atm',
    country STRING COMMENT 'Merchant country',
    city STRING COMMENT 'Merchant city',
    created_at TIMESTAMP COMMENT 'Record creation timestamp'
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/merchants/'
TBLPROPERTIES (
    'classification'='parquet',
    'compressionType'='snappy',
    'parquet.compression'='SNAPPY'
);

-- =============================================================================
-- CUSTOMERS TABLE (partitioned by country)
-- =============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS conversational_analytics.customers (
    customer_id STRING COMMENT 'Unique customer identifier',
    email STRING COMMENT 'Customer email',
    first_name STRING COMMENT 'First name',
    last_name STRING COMMENT 'Last name',
    date_of_birth DATE COMMENT 'Birth date',
    customer_type STRING COMMENT 'personal or business',
    membership_tier STRING COMMENT 'standard, plus, gold, metal, or select',
    registration_date DATE COMMENT 'Registration date',
    user_status STRING COMMENT 'active or dormant',
    created_at TIMESTAMP COMMENT 'Record creation timestamp'
)
PARTITIONED BY (country STRING)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/customers/'
TBLPROPERTIES (
    'classification'='parquet',
    'compressionType'='snappy',
    'parquet.compression'='SNAPPY'
);

-- =============================================================================
-- CARDS TABLE (partitioned by country, year, month)
-- =============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS conversational_analytics.cards (
    card_id STRING COMMENT 'Unique card identifier',
    customer_id STRING COMMENT 'Customer foreign key',
    card_type STRING COMMENT 'virtual or physical',
    card_network STRING COMMENT 'mastercard',
    last_four_digits STRING COMMENT 'Last 4 digits of card',
    expiry_date DATE COMMENT 'Card expiration date',
    issue_date DATE COMMENT 'Card issue date',
    delivery_date DATE COMMENT 'Card delivery date',
    delivery_type STRING COMMENT 'express or standard delivery',
    order_type STRING COMMENT 'initial, reorder, or replacement_expired',
    activation_date DATE COMMENT 'Card activation date',
    campaign_code STRING COMMENT 'Marketing campaign code',
    is_active BOOLEAN COMMENT 'Card active status',
    created_at TIMESTAMP COMMENT 'Record creation timestamp'
)
PARTITIONED BY (
    country STRING,
    year BIGINT,
    month BIGINT
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/cards/'
TBLPROPERTIES (
    'classification'='parquet',
    'compressionType'='snappy',
    'parquet.compression'='SNAPPY'
);

-- =============================================================================
-- TRANSACTIONS TABLE (partitioned by country, year, month)
-- =============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS conversational_analytics.transactions (
    transaction_id STRING COMMENT 'Unique transaction identifier',
    card_id STRING COMMENT 'Card foreign key',
    merchant_id STRING COMMENT 'Merchant foreign key',
    amount_cents BIGINT COMMENT 'Transaction amount in cents',
    currency STRING COMMENT 'Currency code',
    transaction_date TIMESTAMP COMMENT 'Transaction timestamp',
    authorization_code STRING COMMENT 'Auth code',
    is_approved BOOLEAN COMMENT 'Approval status',
    decline_reason STRING COMMENT 'Decline reason if rejected'
)
PARTITIONED BY (
    country STRING,
    year BIGINT,
    month BIGINT
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/transactions/'
TBLPROPERTIES (
    'classification'='parquet',
    'compressionType'='snappy',
    'parquet.compression'='SNAPPY'
);

-- =============================================================================
-- TOKENIZATIONS TABLE (partitioned by wallet_type)
-- =============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS conversational_analytics.tokenizations (
    tokenization_id STRING COMMENT 'Unique tokenization identifier',
    card_id STRING COMMENT 'Card foreign key',
    token_requestor_id STRING COMMENT 'Token requestor ID',
    tokenization_date TIMESTAMP COMMENT 'Tokenization timestamp',
    customer_registration_date DATE COMMENT 'Customer registration date',
    days_to_tokenize BIGINT COMMENT 'Days from registration to tokenization'
)
PARTITIONED BY (wallet_type STRING)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/tokenizations/'
TBLPROPERTIES (
    'classification'='parquet',
    'compressionType'='snappy',
    'parquet.compression'='SNAPPY'
);

-- =============================================================================
-- CHARGEBACKS TABLE (partitioned by year, month) - Core for UC-2 Analysis
-- =============================================================================
CREATE EXTERNAL TABLE IF NOT EXISTS conversational_analytics.chargebacks (
    chargeback_id STRING COMMENT 'Unique chargeback identifier',
    transaction_id STRING COMMENT 'Transaction foreign key',
    card_id STRING COMMENT 'Card foreign key',
    merchant_id STRING COMMENT 'Merchant foreign key',
    chargeback_date DATE COMMENT 'Chargeback filing date',
    chargeback_amount_cents BIGINT COMMENT 'Chargeback amount in cents',
    currency STRING COMMENT 'Currency code',
    chargeback_type STRING COMMENT 'unauthorized or authorized',
    reason_code STRING COMMENT 'Chargeback reason code',
    status STRING COMMENT 'Chargeback status',
    resolution_date DATE COMMENT 'Resolution date'
)
PARTITIONED BY (
    year BIGINT,
    month BIGINT
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/chargebacks/'
TBLPROPERTIES (
    'classification'='parquet',
    'compressionType'='snappy',
    'parquet.compression'='SNAPPY'
);
