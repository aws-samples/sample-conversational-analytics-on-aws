# Architecture

## Executive Summary

This sample is a demonstration data platform that proves AI can reason through financial data, not just produce static reports. Built on Amazon Quick (formerly Amazon QuickSight), the platform enables Product Managers from AnyCompany Bank's Cards & Payments domain to ask complex analytical questions in plain English and receive accurate, data-driven answers.

The platform contains synthetic data for 8 European markets with intentionally embedded patterns and anomalies. When a Product Manager asks "Why did chargebacks increase last week?", the AI doesn't just show a chart — it identifies the specific merchant causing the spike, the type of fraud involved, and the reason codes behind it. This is the difference between reporting and reasoning.

### What It Proves

| Capability | Example |
|---|---|
| Pattern Discovery | AI identifies that Spanish users tokenize cards within 3 days, while German users take 12 days |
| Root Cause Analysis | AI traces a chargeback spike to a single e-commerce merchant committing card-not-present fraud |
| Segment Intelligence | AI understands that "best customers" means Metal tier and shows their spending preferences |
| Cross-Domain Reasoning | AI connects customer profiles, card products, transactions, and merchant data to answer multi-dimensional questions |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCT MANAGER (Natural Language)                   │
│                                                                             │
│   "Why did chargebacks increase last week?"                                 │
│   "How long after joining should we push users to tokenize?"                │
│   "What merchants do our best customers prefer?"                            │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COGNITIVE LAYER                                     │
│                                                                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────────────┐  │
│  │   Chat Agent     │  │   Q Topics       │  │   Business Glossary       │  │
│  │   Persona        │  │   (Semantic       │  │   (Domain Knowledge)      │  │
│  │                  │  │    Model)         │  │                           │  │
│  │ • Behavioral     │  │ • Column &        │  │ • 200+ business term      │  │
│  │   rules          │  │   cell value      │  │   definitions             │  │
│  │ • Business       │  │   synonyms        │  │ • Metric formulas         │  │
│  │   language       │  │ • Custom          │  │ • Entity relationships    │  │
│  │ • Fallback       │  │   instructions    │  │ • Query vocabulary        │  │
│  │   SQL guidance   │  │ • Dataset-to-     │  │ • Time & trend terms      │  │
│  │                  │  │   question        │  │                           │  │
│  │                  │  │   routing         │  │                           │  │
│  └─────────────────┘  └──────────────────┘  └───────────────────────────┘  │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SEMANTIC LAYER                                      │
│                        (AWS QuickSight DataSets)                             │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │  Spending     │ │ Tokenization │ │  Chargeback   │ │  Customer    │       │
│  │  Analysis     │ │  Analysis    │ │  Analysis     │ │  Cards       │       │
│  │              │ │              │ │              │ │              │       │
│  │ Txn+Card+    │ │ Token+Card+  │ │ CB+Txn+      │ │ Card+        │       │
│  │ Customer+    │ │ Customer     │ │ Merchant     │ │ Customer     │       │
│  │ Merchant     │ │              │ │              │ │              │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                     ┌──────────────┐       │
│                                                     │ Card          │       │
│                                                     │ Delivery      │       │
│                                                     │              │       │
│                                                     │ Physical     │       │
│                                                     │ cards only   │       │
│                                                     └──────────────┘       │
│                                                                             │
│  + 6 raw table datasets (customers, cards, transactions, tokenizations,     │
│    chargebacks, merchants)                                                  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          QUERY ENGINE                                        │
│                        (Amazon Athena — Serverless SQL)                       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          METADATA CATALOG                                    │
│                        (AWS Glue Data Catalog)                               │
│                                                                             │
│  Database: conversational_analytics                                                            │
│  Tables: customers, cards, transactions, tokenizations, chargebacks,        │
│          merchants                                                          │
│  Format: Apache Parquet (columnar, compressed)                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA LAKE                                           │
│                        (Amazon S3)                                            │
│                                                                             │
│  100K customers · 120K cards · 5M transactions · 70K tokenizations          │
│  25K chargebacks · 10K merchants                                            │
│  Partitioned by country, year, month for query performance                  │
│  8 European markets: ES, DE, UK, FR, IT, NL, PL, PT                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Data Foundation

The platform generates synthetic but realistic financial data for a fictional European neobank ("AnyCompany Bank") operating across 8 countries. The data covers the full cards lifecycle: customer onboarding, card issuance and delivery, transactions at merchants, digital wallet tokenization, and chargeback disputes.

Critically, the data contains 6 intentionally embedded patterns that mimic real-world business phenomena. These patterns are what the AI must discover — they serve as the test cases proving the system works.

### 2. Data Lake & Query Infrastructure

Data is stored as compressed Parquet files in Amazon S3, organized with Hive-style partitioning (by country, year, month) for efficient querying. AWS Glue Data Catalog provides the metadata layer, and Amazon Athena enables serverless SQL queries without managing any database infrastructure.

### 3. Semantic Layer — Pre-Joined Analytical Views

A key design decision: QuickSight's AI works best when it doesn't need to figure out how to JOIN tables. The platform provides 5 pre-joined datasets, each purpose-built for a specific analytical domain:

| Analytical View | What It Combines | Answers Questions Like |
|---|---|---|
| Spending Analysis | Transactions + Cards + Customers + Merchants | "What do premium customers spend on?" |
| Tokenization Analysis | Tokenizations + Cards + Customers | "How fast do users adopt digital wallets?" |
| Chargeback Analysis | Chargebacks + Transactions + Merchants | "Why did disputes spike last week?" |
| Customer Cards | Cards + Customers | "How many cards does a typical business user have?" |
| Card Delivery | Cards (physical only, with calculated delivery time) | "Which country has the slowest card delivery?" |

Each view is designed around a specific grain (one row = one transaction, one chargeback, one card, etc.) so the AI knows exactly what it's counting and aggregating.

### 4. Cognitive Layer — Teaching the AI to Think Like a Product Manager

This is the most important part of the architecture. The cognitive layer is what transforms a generic AI into a domain expert that understands AnyCompany Bank's business. It is distributed across three components that work together:

#### Q Topics (Semantic Model)

Q Topics define how the AI interprets data columns and values. They contain:

- Column synonyms — so the AI knows that "spend" means `amount_cents`, "fraud" means `chargeback_type = 'unauthorized'`, and "premium customers" means `membership_tier = 'metal'`
- Cell value synonyms — so the AI maps "Spain" to `ES`, "Apple Pay" to `apple_pay`, "groceries" to MCC code `5411`
- Custom instructions — routing rules that tell the AI which pre-joined dataset to use for each type of question
- Aggregation guidance — rules like "always AVERAGE delivery_days, always SUM amount_cents"

#### Chat Agent Persona (Behavioral Rules)

The Chat Agent persona defines how the AI behaves when interacting with Product Managers:

- Always try the Q Topic first; fall back to raw SQL only when necessary
- Use business language, not database jargon ("premium customers" not "membership_tier = 'metal'")
- Monetary values are in cents — always divide by 100 for display
- Never guess — ask for clarification when the question is ambiguous
- Translate MCC codes to human-readable category names

#### Business Glossary (Domain Knowledge)

A comprehensive vocabulary document that teaches the AI AnyCompany Bank's specific terminology:

- Customer segments: Metal tier (best customers), MAU (Monthly Active User), Dormant
- 200+ synonym mappings across 21 categories (customer types, membership tiers, merchant categories, chargeback types, etc.)
- Metric definitions with formulas (Chargeback Rate, Average Transaction Value, Card Density)
- Time-based query terms (last week, MTD, YTD, Q1-Q4)
- Analysis vocabulary (spike, trend, breakdown, compare)

This three-part cognitive design means the AI's "knowledge" is not hardcoded in one place — it's layered. The Q Topic handles data interpretation, the persona handles behavior, and the glossary handles domain expertise.

---

## The 6 Use Cases

Each use case represents a real question a Product Manager would ask. The platform has embedded specific patterns in the data that the AI must discover.

### UC-1: Tokenization Timing
> "How long after joining should we push users to tokenize their cards?"

The AI discovers that tokenization timing varies dramatically by country — Spanish users add cards to digital wallets within 3 days, while German users take 12 days. This insight directly informs when to send push notifications by market.

### UC-2: Chargeback Root Cause
> "Why did chargebacks increase in the week of January 15th?"

The AI traces a 3.5x chargeback spike to a single e-commerce merchant ("FastShop Online"), identifies that 85% of the spike is unauthorized fraud, and pinpoints card-not-present fraud as the dominant reason code. This is multi-step reasoning, not a simple lookup.

### UC-3: Best Customer Spending
> "What type of merchants do our best customers prefer?"

The AI interprets "best customers" as Metal and Plus tier members, then shows they prefer Travel and Restaurants, while Standard tier users gravitate toward Groceries and Gas Stations. This requires understanding both the business terminology and the spending data.

### UC-4: Card Delivery Performance
> "Is there a country where card delivery takes longer?"

The AI identifies Germany as the slowest market (8 days express, 15 days standard) compared to Spain (3 days express, 7 days standard), automatically excluding virtual cards from the analysis since they have no physical delivery.

### UC-5: Campaign Success
> "Do users with Christmas special cards spend more than regular users?"

The AI compares XMAS_2025 cardholders against regular users, finding a 40% spending increase concentrated in Jewelry and Toys categories. This validates the campaign's commercial impact.

### UC-6: User Profiling
> "How many cards on average does a Spanish business metal user have?"

The AI returns 2.3 active cards per business Metal user in Spain, compared to 1.1 for personal users — correctly filtering to active cards only and segmenting by customer type, membership tier, and country simultaneously.

---

## Data Model

The platform models 6 interconnected entities covering the full cards lifecycle:

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  CUSTOMERS   │       │    CARDS     │       │ TRANSACTIONS │
│              │       │              │       │              │
│  100K users  │──────►│  120K cards  │──────►│   5M txns    │
│  8 countries │       │  virtual &   │       │  at 10K      │
│  5 tiers     │       │  physical    │       │  merchants   │
└──────────────┘       └──────┬───────┘       └──────┬───────┘
                              │                      │
              ┌───────────────┼──────────────────────┘
              ▼               ▼                      
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│TOKENIZATIONS │       │ CHARGEBACKS  │       │  MERCHANTS   │
│              │       │              │       │              │
│  70K events  │       │  25K disputes│       │  10K stores  │
│  4 wallet    │       │  fraud &     │       │  14 MCCs     │
│  types       │       │  legitimate  │       │  3 channels  │
└──────────────┘       └──────────────┘       └──────────────┘
```

Key relationships:
- A customer owns multiple cards (personal avg 1.1, business Metal avg 2.3)
- A card generates transactions at merchants
- A card can be tokenized into digital wallets (Apple Pay, Google Pay, Samsung Pay, Garmin Pay)
- A transaction can result in a chargeback dispute
- Merchants are categorized by MCC code and channel (in-store, online, ATM)

---

## Technology Stack

| Layer | Service | Role |
|---|---|---|
| Storage | Amazon S3 | Data lake with Parquet files, Hive-style partitioning |
| Metadata | AWS Glue Data Catalog | Schema registry, table definitions, partition management |
| Query | Amazon Athena | Serverless SQL engine over S3 data |
| Semantic | Amazon QuickSight DataSets | Pre-joined analytical views with column metadata |
| Cognitive | Amazon QuickSight Q Topics | Synonym mappings, custom instructions, query routing |
| Interaction | Amazon QuickSight Chat Agent | Natural language interface with persona and business context |
| Infrastructure | AWS CDK (Python) | Infrastructure as code, 5 deployment stacks |
| Data Generation | Python (Faker, Pandas, PyArrow) | Synthetic data with embedded discoverable patterns |
