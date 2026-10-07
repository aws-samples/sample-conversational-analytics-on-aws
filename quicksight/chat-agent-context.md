# QuickSight Chat Agent - Business Context

## Project Overview

This is a demonstration data platform for conversational analytics with Amazon Quick. The platform contains synthetic data for AnyCompany Bank's Cards domain with **intentionally embedded patterns and anomalies** that you can discover through natural language queries.

**Primary Goal:** Prove AI can reason through data, not just produce static reports.

**Compliance note:** all customer and card data here is synthetic. Real EU personal data or payment card data would fall under GDPR and PCI DSS, which are the deployer's responsibility.

## 6 Use Cases to Support

### UC-1: Tokenization Timing Analysis

**Question:** "How long after joining should we push users to tokenize their cards?"

### UC-2: Chargeback Root Cause Analysis

**Question:** "Why did chargebacks increase in the week of January 15th, 2026?"

### UC-3: Best Customer Spending Habits

**Question:** "What type of merchants do our best customers prefer?"

### UC-4: Card Delivery Performance

**Question:** "Is there a country where card delivery takes longer?"

### UC-5: Campaign Success Analysis

**Question:** "Do users with Christmas special cards spend more than regular users?"

### UC-6: User Profiling

**Question:** "How many cards on average does a Spanish business metal user have?"

---

## Athena Data Schema

All tables are in the `conversational_analytics` database. Use `conversational_analytics.` prefix in all queries.

### Dimension Tables

**conversational_analytics.merchants** (no partitioning)
```
merchant_id             STRING    -- Primary key
merchant_name           STRING    -- Business name
merchant_category_code  STRING    -- MCC code (e.g. '5411')
merchant_category_name  STRING    -- MCC description (e.g. 'Groceries')
channel                 STRING    -- pos, ecom, atm
country                 STRING    -- ISO country code
city                    STRING    -- Merchant city
created_at              TIMESTAMP
```

**conversational_analytics.customers** (partitioned by country)
```
customer_id        STRING    -- Primary key
email              STRING
first_name         STRING
last_name          STRING
date_of_birth      DATE
customer_type      STRING    -- personal, business
membership_tier    STRING    -- standard, plus, gold, metal, select
registration_date  DATE
user_status        STRING    -- active, dormant
created_at         TIMESTAMP
-- Partition: country STRING
```

**conversational_analytics.cards** (partitioned by country, year, month)
```
card_id            STRING    -- Primary key
customer_id        STRING    -- FK -> customers
card_type          STRING    -- virtual, physical
card_network       STRING    -- mastercard
last_four_digits   STRING
expiry_date        DATE
issue_date         DATE
delivery_date      DATE
delivery_type      STRING    -- express, standard
order_type         STRING    -- initial, reorder, replacement_expired, additional
activation_date    DATE
campaign_code      STRING    -- e.g. 'XMAS_2025' or NULL
is_active          BOOLEAN
created_at         TIMESTAMP
-- Partitions: country STRING, year BIGINT, month BIGINT
```

### Fact Tables

**conversational_analytics.transactions** (partitioned by country, year, month)
```
transaction_id     STRING    -- Primary key
card_id            STRING    -- FK -> cards
merchant_id        STRING    -- FK -> merchants
amount_cents       BIGINT    -- Amount in cents (divide by 100 for EUR)
currency           STRING
transaction_date   TIMESTAMP
authorization_code STRING
is_approved        BOOLEAN
decline_reason     STRING    -- NULL if approved
-- Partitions: country STRING, year BIGINT, month BIGINT
```

**conversational_analytics.chargebacks** (partitioned by year, month)
```
chargeback_id           STRING    -- Primary key
transaction_id          STRING    -- FK -> transactions
card_id                 STRING    -- FK -> cards
merchant_id             STRING    -- FK -> merchants
chargeback_date         DATE
chargeback_amount_cents BIGINT    -- Amount in cents
currency                STRING
chargeback_type         STRING    -- unauthorized, authorized
reason_code             STRING    -- e.g. fraud_card_not_present
status                  STRING    -- pending, won, lost, expired
resolution_date         DATE
-- Partitions: year BIGINT, month BIGINT
```

**conversational_analytics.tokenizations** (partitioned by wallet_type)
```
tokenization_id             STRING    -- Primary key
card_id                     STRING    -- FK -> cards
token_requestor_id          STRING
tokenization_date           TIMESTAMP
customer_registration_date  DATE
days_to_tokenize            BIGINT    -- Days from registration to tokenization
-- Partition: wallet_type STRING (apple_pay, google_pay, samsung_pay, garmin_pay)
```

---

## JOIN Paths

**Transaction Analysis** (transaction -> card -> customer + merchant):
```sql
FROM conversational_analytics.transactions t
JOIN conversational_analytics.cards c ON t.card_id = c.card_id
JOIN conversational_analytics.customers cu ON c.customer_id = cu.customer_id
JOIN conversational_analytics.merchants m ON t.merchant_id = m.merchant_id
```

**Chargeback Analysis** (chargeback -> transaction + merchant + card -> customer):
```sql
FROM conversational_analytics.chargebacks cb
JOIN conversational_analytics.transactions t ON cb.transaction_id = t.transaction_id
JOIN conversational_analytics.merchants m ON cb.merchant_id = m.merchant_id
JOIN conversational_analytics.cards c ON cb.card_id = c.card_id
JOIN conversational_analytics.customers cu ON c.customer_id = cu.customer_id
```

**Tokenization Analysis** (tokenization -> card -> customer):
```sql
FROM conversational_analytics.tokenizations tk
JOIN conversational_analytics.cards c ON tk.card_id = c.card_id
JOIN conversational_analytics.customers cu ON c.customer_id = cu.customer_id
```

---

## SQL Query Guidelines

1. **Always qualify table names** with the `conversational_analytics.` database prefix.
2. **Use partition filters** when possible (country, year, month) for performance.
3. **Filter before aggregating** - use WHERE, not HAVING, for dimension filters.
4. **Exclude virtual cards** from delivery analysis: `WHERE card_type = 'physical'`.
5. **Currency is in cents** - always `/ 100.0` when presenting amounts.
6. **Non-additive measures must be recalculated** from raw data:
   - Rates/Ratios: `COUNT(chargebacks) / COUNT(transactions)` (never SUM pre-computed rates)
   - Averages: `SUM(amount_cents) / COUNT(*)` (never AVG of averages)
   - Percentiles: `APPROX_PERCENTILE(days_to_tokenize, 0.8)`

---

## Example SQL Queries

**Tokenization timing by country (80th percentile):**
```sql
SELECT cu.country,
       APPROX_PERCENTILE(tk.days_to_tokenize, 0.8) AS p80_days
FROM conversational_analytics.tokenizations tk
JOIN conversational_analytics.cards c ON tk.card_id = c.card_id
JOIN conversational_analytics.customers cu ON c.customer_id = cu.customer_id
GROUP BY cu.country
ORDER BY p80_days;
```

**Chargeback spike analysis by merchant:**
```sql
SELECT m.merchant_name,
       cb.chargeback_type,
       COUNT(*) AS count
FROM conversational_analytics.chargebacks cb
JOIN conversational_analytics.merchants m ON cb.merchant_id = m.merchant_id
WHERE cb.chargeback_date >= DATE '...'  -- adjust date range
  AND cb.chargeback_date <= DATE '...'  -- adjust date range
GROUP BY m.merchant_name, cb.chargeback_type
ORDER BY count DESC;
```

**Spending by membership tier and merchant category:**
```sql
SELECT cu.membership_tier,
       m.merchant_category_name,
       SUM(t.amount_cents) / 100.0 AS spend_eur
FROM conversational_analytics.transactions t
JOIN conversational_analytics.cards c ON t.card_id = c.card_id
JOIN conversational_analytics.customers cu ON c.customer_id = cu.customer_id
JOIN conversational_analytics.merchants m ON t.merchant_id = m.merchant_id
WHERE t.is_approved = true
GROUP BY cu.membership_tier, m.merchant_category_name
ORDER BY cu.membership_tier, spend_eur DESC;
```

**Average cards per Spanish business customer:**
```sql
SELECT cu.customer_type,
       ROUND(1.0 * COUNT(c.card_id) / COUNT(DISTINCT cu.customer_id), 2) AS avg_cards
FROM conversational_analytics.customers cu
JOIN conversational_analytics.cards c ON cu.customer_id = c.customer_id
WHERE c.is_active = true AND cu.country = 'ES'
GROUP BY cu.customer_type;
```

---

## Data Volumes

Row counts depend on the data tier that was loaded (S, M or L; each tier is 10x the previous one). Never state a row count from memory; run `COUNT(*)` when the user asks. Relative sizes are stable across tiers:

| Table | Records (relative to customers) | Partitioning |
|-------|---------------------------------|-------------|
| customers | 1x | country |
| cards | ~1.2x | country, year, month |
| transactions | 50x | country, year, month |
| tokenizations | ~0.7x | wallet_type |
| chargebacks | 0.25x | year, month |
| merchants | 0.1x | none |
