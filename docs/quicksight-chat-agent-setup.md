# Chat Agent Setup Guide

The `ConversationalAnalytics-QuickSight-ChatAgent` stack creates an Amazon Quick custom chat agent, **Cards Analyst**, that answers questions about AnyCompany Bank's Cards domain data.

## Prerequisites

1. The `ConversationalAnalytics-Infra`, `ConversationalAnalytics-GlueTables`, `ConversationalAnalytics-QuickSight` and `ConversationalAnalytics-QuickSight-Topics` stacks are deployed. The agent stack imports the `conversational-analytics-demo` group ARN from `ConversationalAnalytics-QuickSight`.
2. Data is uploaded to S3 and the Athena tables exist (`scripts/create_tables.py`).
3. Your Region supports Amazon Quick agentic features (see [Prerequisites](../README.md#prerequisites)).
4. The custom-resource Lambda can reach the public npm registry (see [How it works](#how-it-works)).

## Deploy

```bash
uv run cdk deploy ConversationalAnalytics-QuickSight-ChatAgent
```

The stack outputs the agent ID (`conversational-analytics-cards-chat-agent`) and ARN. The agent then shows up under **Chat agents** in the Amazon Quick console for the configured user and members of the `conversational-analytics-demo` group.

## How it works

The agent is a native `AWS::QuickSight::Agent` resource (`quicksight.CfnAgent`), so CloudFormation creates, updates and deletes it. That resource type has no permissions property, so the stack shares the agent by calling `UpdateAgentPermissions` through `AwsCustomResource`:

- **Instructions:** at synth time the stack concatenates two versioned Markdown files into the agent's `CustomInstructions`. It fails the synth if the result is over the API's 350,000-character limit.
  - `quicksight/chat-agent-prompt.md`: the persona, behaviour rules, glossary and non-additive measure rules.
  - `quicksight/chat-agent-context.md`: the business context, Athena schema, join paths and query guidelines for the SQL fallback.
- **Welcome message and starter prompts:** defined in `cdk/stacks/quicksight_chatagent_stack.py` (at most 3 prompts of up to 100 characters each).
- **Permissions:** `UpdateAgentPermissions` grants access to the configured QuickSight user and the `conversational-analytics-demo` group. Use user or group ARNs as principals; namespace ARNs aren't valid.
- **SDK version:** the permissions custom resource needs `install_latest_aws_sdk=True`, because the AWS SDK bundled in the custom-resource Lambda predates the Agent API. The Lambda installs the latest `@aws-sdk/client-quicksight` from npm at deploy time.
- **No Space:** the agent is created without a Space, so it answers over the Topics and datasets the invoking user can access. Attaching a Space through the API passes validation, but then every chat message fails with a generic `400` error. If you need a Space-scoped agent, create it in the console.

## Test the agent

Ask one question per use case and compare the answer with the expected result. Use explicit dates; "last week" depends on when you ask.

| Use case | Question | Expected answer |
|---|---|---|
| Tokenization | How long after joining should we push users to tokenize their cards? | 80th percentile: ES 3 days, UK 7, DE 12 |
| Chargebacks | Why did chargebacks increase in the week of January 15th, 2026? | 3.5x spike, ~80% at FastShop Online (e-commerce), 85% unauthorized, mostly `fraud_card_not_present` |
| Spending | What type of merchants do our best customers prefer? | Metal tier: Travel (Airlines, Hotels) and Restaurants. Standard tier: Groceries and Gas |
| Delivery | Is there a country where card delivery takes longer? | Germany is slowest: 8 days express, 15 standard |
| Campaign | Do users with Christmas special cards spend more? | About 40% more, concentrated in Jewelry and Toys |
| Profiling | How many cards does a Spanish business metal user have? | About 2.3 active cards, vs 1.1 for personal users |

Also check *how* the agent got there. Ask which dataset or query it used: the right number from the wrong dataset is a bug that will surface later.

## Update the agent

1. Edit `quicksight/chat-agent-prompt.md` or `quicksight/chat-agent-context.md`. Keep them in line with `src/conversational_analytics/schema_definitions.py` and the synonyms in `src/conversational_analytics/topic_synonyms.py` / `src/conversational_analytics/joined_dataset_synonyms.py`.
2. Redeploy: `uv run cdk deploy ConversationalAnalytics-QuickSight-ChatAgent`. CloudFormation updates the agent with the new instructions.

When an answer is wrong, the fix is usually in the semantic layer, not the model. Look for a missing synonym, routing hint or aggregation rule.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Deploy fails with an unknown `updateAgentPermissions` action | The Lambda couldn't install the latest SDK (no internet egress to npm) | Allow outbound access for the custom-resource Lambda, or deploy from an account and Region that has it |
| Every chat message returns a `400` error | A Space was attached to the agent through the API | Remove `Spaces` from the stack and redeploy, or create the agent in the console |
| The agent can't find data | Topics missing or empty, or the user lacks dataset permissions | Check that `ConversationalAnalytics-QuickSight-Topics` is deployed and run `scripts/validate_tables.py` |
| The numbers don't match the expected answers | Patterns missing from the loaded data, or stale data | Run `scripts/validate_patterns.py`; regenerate, upload and run `create_tables.py` again |
| Deleting the stack fails | The agent was already deleted by hand | Retry the delete; if the agent resource still fails, skip it in CloudFormation and confirm the agent is gone in the console |
| Deploy fails because agent `conversational-analytics-cards-chat-agent` already exists | The stack was deployed with an older version that created the agent through `AwsCustomResource` | Run `uv run cdk destroy ConversationalAnalytics-QuickSight-ChatAgent`, then deploy again |

## Files

| File | Purpose |
|------|---------|
| `cdk/stacks/quicksight_chatagent_stack.py` | Stack: agent, permissions, welcome message, starter prompts |
| `quicksight/chat-agent-prompt.md` | Persona instructions (behaviour, glossary, rules) |
| `quicksight/chat-agent-context.md` | Business context (schema, join paths, SQL guidelines) |
