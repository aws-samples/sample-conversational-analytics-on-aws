# Conversational Analytics on AWS

Root-cause analysis in plain English with [Amazon Quick](https://aws.amazon.com/quick/): a conversational analytics agent on top of a standard S3, AWS Glue and Amazon Athena lakehouse.

A Product Manager sees chargebacks jump 250% week over week. A dashboard shows the spike but not the cause, and finding it usually means a dozen filter changes and a ticket to the data team. With conversational analytics, the PM asks *"Why did chargebacks increase in the week of January 15th?"*. The chat agent traces the spike to one merchant, fraud type and reason code in a single answer.

The sample uses synthetic card-payments data for a fictional neobank, AnyCompany Bank, in eight European markets. The data contains **patterns embedded on purpose**, so you can check whether the agent finds them from natural-language questions alone (see [Demo Scenarios](#demo-scenarios)).

**What you get:**

- **A semantic layer in three parts:** pre-joined datasets with one grain each, Q Topics with synonyms and routing hints, and a chat agent with a persona, glossary and fallback SQL.
- **No new data platform:** the AI layer sits on top of an existing lakehouse (S3, Glue Data Catalog, Athena).
- **Everything as code:** CDK stacks deploy the infrastructure, datasets, Topics and agent. Synonyms and agent instructions are versioned files, not console settings.
- **Testable AI analytics:** every demo question has a known expected answer, so evaluation is pass or fail rather than "looks plausible".

![Architecture: Amazon S3, AWS Glue Data Catalog and Amazon Athena form the existing lakehouse. Amazon Quick datasets, Q Topics and the chat agent form a three-layer semantic layer on top. The Product Manager asks the chat agent in plain English and gets the root cause back; the agent falls back to SQL through Athena when a Topic can't answer.](docs/images/architecture.png)

The lakehouse holds Parquet files in S3, Hive-partitioned by country and date, with the schema in the Glue Data Catalog and Athena as the query engine. The semantic layer in Amazon Quick adds three things on top:

1. **Datasets** pre-join the tables. Each has one explicit grain, readable columns such as category names next to MCC codes, and derived fields like `delivery_days`.
2. **Q Topics** map business language to data: "Spain" → `ES`, "fraud" → `unauthorized`, "best customers" → metal tier. They also carry routing and aggregation rules.
3. **The chat agent** gets a persona, behaviour rules ("never guess", "amounts are in cents") and the Athena schema, so it can write a fallback SQL query when a Topic can't answer.

Data stays in your AWS account, and every query runs through Athena and is logged in AWS CloudTrail.

> **Note:** this sample uses legacy Q Topics. Amazon Quick now also supports [Dataset Enrichment and multi-dataset Topics](https://aws.amazon.com/blogs/machine-learning/enrich-your-datasets-with-business-context-migrating-from-legacy-topics-to-semantic-datasets-in-amazon-quick/). The same principles apply: one grain per dataset, synonyms as code, explicit aggregation rules.

> **Important:** this sample is for demonstration and educational purposes only and is not intended for production use. It uses synthetic data. Before using any part of it in production, perform your own security testing and review, and work with your security and legal teams to meet your organization's security, regulatory and compliance requirements. You are responsible for the AWS costs it incurs.

## Prerequisites

- **An AWS account** where you can create IAM roles, S3 buckets, Glue, Athena and QuickSight resources.
- **An Amazon Quick (Quick Suite) / Amazon QuickSight Enterprise edition subscription** in the deployment Region.
  - Q Topics need Enterprise edition and an Author or Admin role ([Creating a Topic](https://docs.aws.amazon.com/quick/latest/userguide/topics-create.html)). The pricing page lists "Create Amazon Q Topics" under Author Pro.
  - Custom chat agents (the `ConversationalAnalytics-QuickSight-ChatAgent` stack) are Amazon Quick capabilities. Use an **Amazon Quick Enterprise** user (the Quick Sight **Author Pro** role) for the user that deploys and owns the resources ([user types](https://docs.aws.amazon.com/quick/latest/userguide/user-types.html)).
  - Use a Region where Amazon Quick shows **Agentic Features: Yes**. As of this writing that means us-east-1, us-west-2, eu-west-1, eu-west-2, eu-central-1, ap-southeast-2 and ap-northeast-1 ([Supported Regions](https://docs.aws.amazon.com/quick/latest/userguide/regions.html)).
  - QuickSight must use the default service role `aws-quicksight-service-role-v0`, with Athena access enabled. The `ConversationalAnalytics-QuickSight` stack attaches an inline S3 read policy to that role.
- **A QuickSight user ARN** for the user who will own the datasets, topics, analysis and agent, for example `arn:aws:quicksight:eu-west-1:123456789012:user/default/your-username`.
- **Node.js 22.x or later** and the AWS CDK CLI, pinned to the version this sample was tested with (`npm install -g aws-cdk@2.1144.0`) ([CDK prerequisites](https://docs.aws.amazon.com/cdk/v2/guide/prerequisites.html)). `uv run cdk ...` runs the globally installed `cdk`, because the CLI is not a Python dependency.
- **Python 3.13** (see `.python-version`) and **[uv](https://docs.astral.sh/uv/)**.
- **The AWS CLI and credentials** for the target account, for example from `aws configure` or SSO.
- **A bootstrapped CDK environment** in the target account and Region:
  ```bash
  cdk bootstrap aws://<AWS_ACCOUNT_ID>/<AWS_REGION>
  ```

**Region:** the Region comes from `AWS_REGION` in your `.env.<name>` file. The CDK app exits if it is not set. `.env.example` uses `eu-west-1`, and the Python scripts in `scripts/` also fall back to `eu-west-1` if `AWS_REGION` is unset. Deploy in the same Region as your QuickSight account, and make sure the Region supports agentic features if you deploy the chat agent.

## Cost

You are responsible for the cost of the AWS services used while running this sample. The Amazon Quick / QuickSight subscription is almost always the dominant cost. At S-tier data volumes the data-platform services cost very little.

| Service | What this sample deploys | What drives the cost | Pricing |
|---------|--------------------------|----------------------|---------|
| Amazon Quick / QuickSight | Athena data source, 11 datasets, 2 Q Topics, 1 analysis, 1 chat agent, 1 group | Per-user subscriptions and account-level fees (Q Topics count as Q&A) | [Quick pricing](https://aws.amazon.com/quicksuite/pricing/), [Quick Sight pricing](https://aws.amazon.com/quicksight/pricing/) |
| Amazon Athena | 1 workgroup (10 GB per-query scan cutoff) | Data scanned by `create_tables.py`, the validation scripts and every QuickSight query | [Athena pricing](https://aws.amazon.com/athena/pricing/) |
| Amazon S3 | Data lake bucket and Athena results bucket | Stored Parquet files and query results, plus requests | [S3 pricing](https://aws.amazon.com/s3/pricing/) |
| AWS Glue Data Catalog | 1 database and 6 tables with partitions | Metadata objects and requests | [Glue pricing](https://aws.amazon.com/glue/pricing/) |
| AWS Lambda | The CDK `AwsCustomResource` provider functions | A few invocations per deploy or destroy | [Lambda pricing](https://aws.amazon.com/lambda/pricing/) |
| Amazon CloudWatch Logs | Log groups for the custom-resource functions | A few KB of logs per deploy | [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) |

Notes:

- Check the Quick pricing page for the current free trial. Per-user and per-account fees apply for the billing period even if you tear down the stacks quickly.
- SPICE is not used. Every dataset uses `import_mode="DIRECT_QUERY"` (`cdk/stacks/quicksight_stack.py`), so Athena runs the queries and there are no SPICE capacity charges.
- S-tier data is a few MB in total, so Athena, S3, Glue, Lambda and CloudWatch Logs together typically stay well under $1 for a short demo.

Prices change and vary by Region. Use the [AWS Pricing Calculator](https://calculator.aws/) for an estimate for your own setup.

## Quick Start

```bash
# Install the exact dependency versions pinned in uv.lock
uv sync --frozen

# Set up your environment
cp .env.example .env.<name>
# Edit .env.<name> with your AWS account details
source .env.<name>
```

Required variables (see `.env.example`):

```bash
AWS_ACCOUNT_ID=123456789012
AWS_REGION=eu-west-1
QUICKSIGHT_USER_ARN=arn:aws:quicksight:eu-west-1:123456789012:user/default/your-username
QUICKSIGHT_NAMESPACE=default
S3_BUCKET_PREFIX=conversational-analytics
```

## Deployment

The infrastructure is split into stacks so each layer can be iterated on independently:

| Stack | Resources | Purpose |
|-------|-----------|---------|
| **ConversationalAnalytics-Infra** | S3 buckets, Glue DB, Athena workgroup | Stateful - rarely changes |
| **ConversationalAnalytics-GlueTables** | Glue table definitions | Schema changes |
| **ConversationalAnalytics-QuickSight** | DataSource, DataSets (raw + joined), Group | Stable datasets |
| **ConversationalAnalytics-QuickSight-Topics** | Q Topics (raw + optimized) | Topic iteration (can fail independently) |
| **ConversationalAnalytics-QuickSight-Analysis** | Analysis with ML anomaly detection | Dashboard visualizations (optional) |
| **ConversationalAnalytics-QuickSight-ChatAgent** | Custom chat agent | Conversational interface (optional) |

Q Topics require the underlying tables to exist **and contain data**, so deploy in phases.

### Phase 1: Infrastructure

```bash
uv run cdk deploy ConversationalAnalytics-Infra
uv run cdk deploy ConversationalAnalytics-GlueTables
```

### Phase 2: Generate and load data

```bash
# Generate synthetic data (tiers: S ~30s default, M ~5min, L ~30min+)
uv run python scripts/generate_data.py [S|M|L]

# Upload to S3
uv run python scripts/upload_to_s3.py

# Create Athena tables and repair partitions
uv run python scripts/create_tables.py

# Optional: verify tables and embedded patterns
uv run python scripts/validate_tables.py
uv run python scripts/validate_patterns.py
```

### Phase 3: QuickSight DataSets and Q Topics

```bash
uv run cdk deploy ConversationalAnalytics-QuickSight
uv run cdk deploy ConversationalAnalytics-QuickSight-Topics
```

### Phase 4: Chat agent (optional)

```bash
uv run cdk deploy ConversationalAnalytics-QuickSight-ChatAgent
```

The agent's persona comes from `quicksight/chat-agent-prompt.md`, and its business context from `quicksight/chat-agent-context.md`. See [docs/quicksight-chat-agent-setup.md](docs/quicksight-chat-agent-setup.md).

### Phase 5: Analysis (optional)

```bash
uv run cdk deploy ConversationalAnalytics-QuickSight-Analysis
```

The Analysis is built from `quicksight/analyses/conversational-analytics-cards-health-monitor.json`. To change it, edit it in the QuickSight console, then export and redeploy:

```bash
uv run python scripts/export_analysis_definition.py conversational-analytics-cards-health-monitor
uv run cdk deploy ConversationalAnalytics-QuickSight-Analysis
```

Sheets: Executive Overview, Chargeback Analysis (ML anomaly detection), Tokenization Insights, Customer Segmentation, Delivery Performance.

Non-interactive shells (CI, agents) need `--require-approval never` for stacks with IAM changes.

## Demo Scenarios

Each scenario is a business question that QuickSight Q should answer from the data. The patterns are embedded by the generators in `src/conversational_analytics/generators/` and checked by `scripts/validate_patterns.py`.

### 1. Tokenization timing

> "How long after joining should we push users to add their card to a digital wallet?"

| Country | Days to tokenize (80th percentile) |
|---------|------------------------------------|
| Spain (ES) | 3 |
| UK | 7 |
| Germany (DE) | 12 |

Key columns: `customers.registration_date`, `customers.country`, `tokenizations.days_to_tokenize`, `tokenizations.wallet_type`.

### 2. Chargeback root cause

> "Why did chargebacks increase in the week of January 15th, 2026?"

- Chargebacks are 3.5x baseline during 2026-01-15 to 2026-01-21
- About 80% of the spike comes from one e-commerce merchant, **FastShop Online**
- 85% of spike chargebacks are `unauthorized` (30% at baseline), and 65% of those are `fraud_card_not_present`

Key columns: `chargebacks.chargeback_date`, `chargeback_type`, `reason_code`, `merchants.merchant_name`, `merchants.channel`.

### 3. Best-customer spending

> "What type of merchants do our best customers prefer?"

| Segment | Preferred categories |
|---------|---------------------|
| Metal tier ("best customers") | Travel: Airlines (MCC 3000), Hotels (MCC 7011); Restaurants (MCC 5812) |
| Standard tier | Groceries (MCC 5411), Gas stations (MCC 5541) |

Key columns: `customers.membership_tier`, `merchants.merchant_category_code`, `merchants.merchant_category_name`, `transactions.amount_cents`.

### 4. Card delivery

> "Is there a country where card delivery takes longer?"

| Country | Express (days) | Standard (days) |
|---------|---------------|-----------------|
| Germany (DE) | 8 | 15 |
| UK | 5 | 10 |
| Spain (ES) | 3 | 7 |

Delivery time is the number of days between `cards.issue_date` and `cards.delivery_date`. Virtual cards are excluded.

### 5. Christmas campaign

> "Do users with the Christmas special card spend more than regular users?"

- `XMAS_2025` cardholders spend about 40% more than other cardholders
- Their spending is concentrated in Jewelry (MCC 5944) and Toys (MCC 5945)

Key columns: `cards.campaign_code`, `transactions.amount_cents`, `merchants.merchant_category_code`.

### 6. User profiling

> "How many cards on average does a Spanish business metal user have?"

| Segment (ES) | Avg active cards |
|--------------|-----------------|
| Business, metal tier | 2.3 |
| Personal | 1.1 |

Key columns: `customers.customer_type`, `customers.membership_tier`, `customers.country`, `cards.is_active`.

## Tips for a Good Demo

- **Use explicit dates.** "Last week" depends on when you run the demo. Ask about "the week of January 15th, 2026".
- **Prefer the optimized topic.** Q handles joins poorly, so `conversational-analytics-optimized-topic` uses pre-joined datasets for cross-table questions.
- **Ask with category names.** Users say "restaurants", not "MCC 5812". `merchant_category_name` and the topic synonyms cover this.
- **Have a fallback for the campaign question.** If the before/after framing doesn't work, ask "Show spending by card campaign".

## Data Model

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     CUSTOMERS    │       │      CARDS       │       │   TRANSACTIONS   │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ customer_id (PK) │──┐    │ card_id (PK)     │──┐    │ transaction_id   │
│ country          │  │    │ customer_id (FK) │  │    │ card_id (FK)     │
│ registration_date│  └───►│ card_type        │  └───►│ merchant_id (FK) │
│ customer_type    │       │ card_network     │       │ amount_cents     │
│ membership_tier  │       │ issue_date       │       │ currency         │
│ user_status      │       │ delivery_date    │       │ transaction_date │
│ email            │       │ delivery_type    │       │ is_approved      │
│ date_of_birth    │       │ order_type       │       │ decline_reason   │
└──────────────────┘       │ activation_date  │       │ country          │
                           │ campaign_code    │       └──────────────────┘
                           │ is_active        │
                           │ country          │
                           └──────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  TOKENIZATIONS   │       │   CHARGEBACKS    │       │    MERCHANTS     │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ tokenization_id  │       │ chargeback_id    │       │ merchant_id (PK) │
│ card_id (FK)     │       │ transaction_id   │       │ merchant_name    │
│ wallet_type      │       │ chargeback_date  │       │ merchant_cat_code│
│ tokenization_date│       │ chargeback_type  │       │ merchant_cat_name│
│ days_to_tokenize │       │ reason_code      │       │ channel          │
│ customer_reg_date│       │ status           │       │ country          │
└──────────────────┘       │ resolution_date  │       │ city             │
                           │ chargeback_amt   │       └──────────────────┘
                           └──────────────────┘
```

| Table | Rows (L tier) | Partitioning |
|-------|---------------|--------------|
| customers | 100,000 | country |
| cards | ~120,000 | country, year, month |
| transactions | 5,000,000 | country, year, month |
| tokenizations | 70,000 | wallet_type |
| chargebacks | 25,000 | year, month |
| merchants | 10,000 | none |

### Key enums

| Field | Values |
|-------|--------|
| `customer_type` | personal, business |
| `membership_tier` | standard, plus, gold, metal, select |
| `user_status` | active, dormant |
| `card_type` | virtual, physical |
| `delivery_type` | express, standard |
| `order_type` | initial, reorder, replacement_expired, additional |
| `wallet_type` | apple_pay, google_pay, samsung_pay, garmin_pay |
| `channel` | pos, ecom, atm |
| `chargeback_type` | unauthorized, authorized |
| `reason_code` | fraud_card_not_present, fraud_counterfeit, fraud_lost_stolen, merchandise_not_received, merchandise_defective, duplicate_charge, incorrect_amount, subscription_cancelled, other |
| `status` (chargeback) | pending, won, lost, expired |

`src/conversational_analytics/schema_definitions.py` is the single source of truth for schemas. Changes there flow to the generators, the Glue tables, the QuickSight DataSets and the Athena DDL.

### Design notes

- Amounts are stored as integer cents to avoid floating-point issues
- All timestamps are UTC
- Country codes are ISO 3166-1 alpha-2 (ES, DE, UK, FR, IT, NL, PL, PT)
- Generation uses fixed random seeds, so every run produces the same data
- Data is written as snappy-compressed Parquet, partitioned for Athena

## Q Topics

| Topic | Datasets | Use case |
|-------|----------|----------|
| `conversational-analytics-cards-topic` | 6 raw tables | Simple single-table queries |
| `conversational-analytics-optimized-topic` | 5 pre-joined datasets | Cross-table analytics (recommended) |

Pre-joined datasets:
- `spending-analysis`: transactions + cards + customers + merchants
- `tokenization-analysis`: tokenizations + cards + customers
- `chargeback-analysis`: chargebacks + transactions + merchants
- `customer-cards`: cards + customers
- `card-delivery`: physical cards with calculated delivery days

Column and cell-value synonyms (e.g. "fraud" → `unauthorized`, "best customers" → metal tier) are defined in `src/conversational_analytics/topic_synonyms.py` and `src/conversational_analytics/joined_dataset_synonyms.py`.

## Cleanup

Destroy all stacks:

```bash
uv run cdk destroy --all
```

What this removes:

- **S3 buckets:** both buckets use `removal_policy=RemovalPolicy.DESTROY` and `auto_delete_objects=True` (`cdk/stacks/infra_stack.py`). CDK empties and deletes them, including uploaded data and Athena query results.
- **Athena workgroup:** deleted with `recursive_delete_option=True`, which also removes its saved queries and query history.
- **Glue database and tables:** deleted.
- **QuickSight data source, datasets, Topics and analysis:** deleted. These are native CloudFormation resources.
- **QuickSight group `conversational-analytics-demo` and its memberships:** created by `AwsCustomResource` (CloudFormation has no QuickSight Group resource). Its `on_delete` handlers call `DeleteGroupMembership` and `DeleteGroup`.
- **Chat agent:** deleted. It is a native CloudFormation resource (`AWS::QuickSight::Agent`); its permissions custom resource has no `on_delete` handler, because permissions go with the agent.
- **Inline policy `ConversationalAnalyticsDataLakeAccess` on `aws-quicksight-service-role-v0`:** removed by an `on_delete` handler that calls `DeleteRolePolicy`. The role itself isn't touched.

What is left behind:

- **CloudWatch Logs log group** for the S3 auto-delete Lambda in `ConversationalAnalytics-Infra`. Delete it manually. The `AwsCustomResource` log groups in the QuickSight stacks have 1-week retention and are deleted with their stacks.
- **CDK bootstrap resources** (the `CDKToolkit` stack: staging S3 bucket, ECR repository, IAM roles). Other CDK apps in the account may share them, so this sample doesn't remove them.
- **Local generated data** in `data/` on your machine.
- **Custom-resource failures:** if a custom-resource delete fails (for example, the group or agent was already removed by hand), the stack delete can fail. Check that the `conversational-analytics-demo` group and the `conversational-analytics-cards-chat-agent` agent are gone in the QuickSight console.
- **The Amazon Quick / QuickSight subscription and its users.** `cdk destroy` doesn't touch them, and per-user and account fees keep accruing until you remove the users or unsubscribe. Unsubscribing is an **account-level action**: it affects every QuickSight user, dashboard and dataset in the account and Region, not just this sample. If the account has other QuickSight users, don't cancel the subscription. At most, remove the users you added for this demo, and coordinate with your account administrator.

## Documentation

- [docs/quicksight-chat-agent-setup.md](docs/quicksight-chat-agent-setup.md): chat agent setup
- [docs/lessons-learned.md](docs/lessons-learned.md): QuickSight, CDK and data-generation gotchas
- [docs/cards-business-glossary.md](docs/cards-business-glossary.md): business terms
- [docs/cards-synonyms.md](docs/cards-synonyms.md): Q Topic synonym reference
- [architecture.md](architecture.md): architecture details


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

This sample isn't production-ready (see the notice at the top). The considerations below describe its security posture and what to harden before reusing it.

### Security considerations

- **Compliance (GDPR, PCI DSS).** The schemas model EU personal data (names, email, date of birth) and payment card data (last four digits, transactions, chargebacks). All of it is synthetic. If you adapt the sample to real customer or cardholder data, you're responsible for GDPR, PCI DSS and any other applicable requirements, including data minimisation, encryption with customer-managed keys, access controls (RLS/CLS) and retention.
- **Synthetic data only.** All data comes from `src/conversational_analytics/generators/` with fixed seeds. Names, emails and dates of birth are fake (Faker), and there is no real customer or card data. Don't point this sample at real cardholder data without a proper security review (PCI DSS, PII handling).
- **S3 access logging:** server access logs for both buckets go to a separate access-logs bucket (TLS-only, 30-day expiry).
- **S3:** both buckets use `BlockPublicAccess.BLOCK_ALL` and SSE-S3 encryption (`BucketEncryption.S3_MANAGED`). The Athena workgroup enforces SSE-S3 for query results (`enforce_work_group_configuration=True`). Both buckets deny non-TLS requests (`enforce_ssl=True`).
- **QuickSight service principal access:** the data lake bucket policy grants `quicksight.amazonaws.com` read-only access, conditioned on `aws:SourceAccount`. The Athena results bucket grants read/write with the same condition, which prevents another account's QuickSight from using it.
- **QuickSight service role:** the `ConversationalAnalytics-QuickSight` stack attaches an inline policy to the existing `aws-quicksight-service-role-v0`. The policy grants `s3:GetObject`, `s3:ListBucket` and `s3:GetBucketLocation` on the data lake bucket only.
- **Custom-resource Lambda roles:** each stack uses a dedicated role with a single inline policy (no managed policies). It can write logs only to its stack's log group, and its QuickSight and IAM actions are scoped to this sample's resources:
  - `ConversationalAnalytics-QuickSight`: `iam:PutRolePolicy` / `iam:DeleteRolePolicy` on `aws-quicksight-service-role-v0` only, and group and membership actions on the `conversational-analytics-demo` group only.
  - `ConversationalAnalytics-QuickSight-Topics`: `UpdateTopicPermissions` / `DescribeTopicPermissions` on this sample's two topics only.
  - `ConversationalAnalytics-QuickSight-ChatAgent`: `UpdateAgentPermissions` / `DescribeAgentPermissions` on `agent/conversational-analytics-cards-chat-agent` only. CloudFormation manages the agent itself.
  - The `ConversationalAnalytics-QuickSight` stack modifies the account-wide QuickSight service role. Review this before deploying into an account that other QuickSight workloads use.
- **QuickSight permissions:** only the configured user (`QUICKSIGHT_USER_ARN`) gets owner permissions on the data source, datasets, Topics, analysis and chat agent. The `conversational-analytics-demo` group, which includes every user in `QUICKSIGHT_ADDITIONAL_USERS`, gets read-only access: it can query the datasets, ask the Topics and use the agent, but can't edit, delete or re-share them. Analyses have no viewer role, so the group doesn't get the analysis; share a published dashboard instead.
- **TLS to Athena:** the QuickSight data source sets `disable_ssl=False`.
- **Dependencies:** `pyproject.toml` pins direct dependencies to exact versions, and `uv.lock` pins every package, including transitive ones, to an exact version and hash. Install with `uv sync --frozen` to get exactly the tested set.
- **Configuration and credentials:** account IDs and user ARNs come from `.env.<name>` files. `.gitignore` excludes `.env` and `.env.*` (except `.env.example`). The sample stores no secrets or access keys.
- **Deploy-time dependency download:** the chat agent permissions custom resource uses `install_latest_aws_sdk=True`, so the provider Lambda installs the latest `@aws-sdk/client-quicksight` from npm at deploy time. The Lambda's bundled SDK doesn't include the Agent API yet. This needs internet egress and means the deployed SDK version isn't pinned.

### Responsible AI

The chat agent and Q Topics generate answers with a large language model. Answers can be incomplete or wrong, even when they sound confident. The agent can only reach data the invoking user already has permission to see, and this sample tests it against known answers (see [Demo Scenarios](#demo-scenarios) and `scripts/validate_patterns.py`). Before using a similar setup in production:

- Validate outputs. Check which dataset or query an answer came from, keep a regression set of questions with expected answers, and re-run it after every change to instructions, synonyms or data.
- Keep a human in the loop for decisions that affect customers, such as chargeback disputes or credit actions.
- If you build your own generative components on this data, for example an application on Amazon Bedrock, apply [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) for content filtering, denied topics and PII redaction.
- Tell users that answers are AI-generated, and collect their feedback.

See the [AWS Responsible AI Policy](https://aws.amazon.com/ai/responsible-ai/policy/) for more guidance.

## Authors

- Artem Shchodro
- Pawel Warmuth
- Sascha Möllering

Thanks to Ben Freiberg for reviewing this sample.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute.
