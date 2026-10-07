# Lessons Learned

Non-obvious things that cost us time while building this sample: QuickSight quirks, CDK gotchas,
and data-generation traps. Each entry records the context, the takeaway, and the evidence.

---

## Lessons

### QuickSight

#### physicalTableMap keys reject underscores
- **Date:** 2026-07-01
- **Status:** Active
- **Context:** Creating QuickSight DataSets via CDK/CloudFormation.
- **Lesson:** `physicalTableMap` keys must match `[0-9a-zA-Z-]*` — use hyphens, not
  underscores (`card-transactions-physical`, not `card_transactions_physical`).
- **Why / evidence:** Surfaces as a cryptic `AWS::EarlyValidation::PropertyValidation`
  failure. Testing via `aws quicksight create-data-set` gives a clearer error.

#### Q Topics fail if datasets have no data
- **Date:** 2026-07-01
- **Status:** Active
- **Context:** Deploying the Topics stack.
- **Lesson:** Q Topic creation throws `InternalFailureException` if referenced datasets
  point to non-existent Glue tables, tables that are empty, or queries that fail
  validation. Tables must exist *with data* before topic creation — hence the phased
  deployment and the separate Topics stack.
- **Why / evidence:** Motivated splitting Topics from DataSets so a topic refresh failure
  doesn't roll back the datasets.

#### Chat agents: use native `CfnAgent`, but permissions still need a custom resource
- **Date:** 2026-07-02 (corrected 2026-10-03)
- **Status:** Active
- **Context:** Building `ConversationalAnalytics-QuickSight-ChatAgent`.
- **Lesson:** CloudFormation has an
  [`AWS::QuickSight::Agent`](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-quicksight-agent.html)
  resource type, exposed as `quicksight.CfnAgent` in aws-cdk-lib (present in 2.272.0,
  absent in 2.236.0). The stack uses it for the agent. The resource type has no
  permissions property, so `UpdateAgentPermissions` runs through an `AwsCustomResource`
  with `install_latest_aws_sdk=True` (the Lambda's bundled SDK predates the Agent API).
  Use User/Group ARNs as permission principals (not Namespace ARNs). Persona and
  business context go in `CustomPromptInput.NewPrompt.CustomInstructions` (5 to 350000
  chars).
- **Why / evidence:** An earlier version of this entry said the resource type didn't
  exist, and the stack drove `CreateAgent`/`UpdateAgent`/`DeleteAgent` through
  `AwsCustomResource`. A security review pointed out the resource exists. Checked
  against the CloudFormation template reference and the aws-cdk-lib packages. Stacks
  deployed with the old custom resource can't be updated in place: CloudFormation
  creates the new agent (same `AgentId`) before deleting the old one, so destroy the
  ChatAgent stack and redeploy. See `cdk/stacks/quicksight_chatagent_stack.py`.

#### Attaching a Space to a chat agent via the API breaks chat
- **Date:** 2026-07-02
- **Status:** Active
- **Context:** Tried scoping the chat agent to the optimized Q Topic via a `Spaces` list
  on `CreateAgent`/`UpdateAgent`.
- **Lesson:** Do NOT attach a `Spaces` list to an agent created via the API. It passes
  create-time validation but every chat message then fails with a generic
  `400 "An internal server error occurred"`, and the console shows the knowledge
  resource as "resource unavailable" / `RESOURCE_NOT_FOUND`. Create the agent WITHOUT a
  Space — it answers over whatever Q Topics/datasets the invoking user can access, like
  console-created agents. If you truly need a space-scoped agent, build it in the console.
- **Why / evidence:** The API records the space ARN but doesn't register the agent↔space
  binding in the backing Q Business layer (`QbsAwsAccountId`/`ModelProfileId`) the way
  the console does. Isolation test (eu-west-1): `Spaces: None` → chat works;
  Lambda-created space → "resource unavailable"; known-good *console-created* space →
  `RESOURCE_NOT_FOUND`. The known-good space failing too proves it's the API binding, not
  the space. Docstring in `quicksight_chatagent_stack.py` warns not to re-add without
  re-testing chat.

#### Topic and agent permission sets are all-or-nothing
- **Date:** 2026-10-01
- **Status:** Active
- **Context:** Giving the `conversational-analytics-demo` group read-only access.
- **Lesson:** `UpdateTopicPermissions` accepts exactly two sets: viewer `["quicksight:DescribeTopic"]` or the full 11-action owner set. Anything in between fails with "unsupported permission sets". The agent viewer set is `["quicksight:DescribeAgent"]`. Analyses have no viewer set at all (sharing makes co-owners), so share a dashboard for read-only access.
- **Why / evidence:** The error message lists the valid sets, so check it before guessing.

#### `aws:SourceAccount` works on the Athena results bucket policy
- **Date:** 2026-10-01
- **Status:** Active
- **Context:** Closing the confused-deputy gap on the QuickSight → Athena results bucket grant.
- **Lesson:** An older note said QuickSight connection tests fail with `aws:SourceAccount` on this statement. A clean deploy with the condition passed: QuickSight's "Athena JDBC driver connection test" queries and all dataset and Topic queries succeeded.
- **Why / evidence:** 50/50 recent queries in `conversational-analytics-workgroup` SUCCEEDED after deploying with the condition.

### CDK / Deployment

#### Athena results bucket name must match the managed-policy prefix
- **Date:** 2026-07-01
- **Status:** Active
- **Context:** Wiring Athena → QuickSight permissions.
- **Lesson:** Name the Athena results bucket `aws-athena-query-results-*` so QuickSight's
  `AWSQuicksightAthenaAccess` managed policy grants S3 access automatically — avoids a
  custom bucket policy.
- **Why / evidence:** The managed policy scopes to that prefix.

#### Exported analysis definitions need ISO timestamps
- **Date:** 2026-10-01
- **Status:** Active
- **Context:** Deploying an analysis from `describe_analysis_definition` output.
- **Lesson:** Serializing boto3 datetimes with `json.dump(default=str)` writes `2025-12-01 01:00:00+01:00`. CloudFormation early validation rejects that; it needs ISO 8601 with a `T`. `export_analysis_definition.py` now uses `isoformat()`.
- **Why / evidence:** `AWS::EarlyValidation::PropertyValidation` on `TimeRangeFilter/RangeMinimumValue/StaticValue`.

### Data Generation

_No lessons captured yet._
