# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""QuickSight Topics Stack - Q Topics for natural language queries.

This stack creates QuickSight Q Topics that enable natural language queries
against the datasets created by the QuickSight stack.

The stack is intentionally separated from the QuickSight DataSets stack because
CloudFormation waits for Q Topic refresh to complete. With Custom SQL datasets,
refresh often fails during iteration. By separating the stacks:
- If Topic refresh fails, only this stack rolls back
- DataSets remain intact in the other stack
- Faster iteration on Topic configuration

Prerequisites:
- ConversationalAnalytics-QuickSight stack deployed (creates DataSource, DataSets, Group)

Deployment:
    uv run cdk deploy ConversationalAnalytics-QuickSight-Topics

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import sys
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Fn
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_quicksight as quicksight
from aws_cdk import custom_resources as cr
from cdk_nag import NagSuppressions
from constructs import Construct

# Add src to path for schema imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from conversational_analytics.joined_dataset_synonyms import (
    COUNTRY_SYNONYMS as JOINED_COUNTRY_SYNONYMS,
)
from conversational_analytics.joined_dataset_synonyms import (
    JOINED_CELL_VALUE_SYNONYMS,
    JOINED_COLUMN_SYNONYMS,
    OPTIMIZED_TOPIC_INSTRUCTIONS,
)
from conversational_analytics.joined_datasets import JOINED_DATASETS
from conversational_analytics.schema_definitions import QUICKSIGHT_TABLES, QuickSightColumn
from conversational_analytics.topic_synonyms import (
    CELL_VALUE_SYNONYMS,
    COLUMN_SYNONYMS,
    COUNTRY_SYNONYMS,
)

# Read-only permission set for the conversational-analytics-demo group: ask questions, no edit/delete/re-share.
# UpdateTopicPermissions only accepts this viewer set or the full owner set.
TOPIC_READER_ACTIONS = ["quicksight:DescribeTopic"]


class QuickSightTopicsStack(cdk.Stack):
    """QuickSight Q Topics stack for Conversational Analytics.

    Creates:
    - Q Topic with raw tables (simple queries)
    - Optimized Q Topic with pre-joined datasets (cross-table analytics)
    - Topic permissions for user and group

    The raw tables topic uses the 6 base tables directly.
    The optimized topic uses 5 pre-joined datasets for complex analytics.

    Prerequisites:
    - QuickSightStack deployed (DataSource, DataSets, Group)
    - Data loaded into S3 and partitions repaired
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        quicksight_user_arn: str,
        quicksight_namespace: str = "default",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.quicksight_user_arn = quicksight_user_arn
        self.quicksight_namespace = quicksight_namespace

        # Import values from QuickSight stack
        self.quicksight_group_arn = Fn.import_value("ConversationalAnalytics-QuickSightGroup")
        self.datasource_arn = Fn.import_value("ConversationalAnalytics-QuickSightDataSource")

        # Group name must match what's in the QuickSight stack
        self.group_name = "conversational-analytics-demo"

        # Create custom resource role for topic permissions
        self._create_custom_resource_log_group()
        self._create_custom_resource_role()

        # Create Q Topic for natural language queries (raw tables)
        self._create_quicksight_topic()

        # Grant Topic permissions via Custom Resource
        self._grant_topic_permissions()

        # Create optimized Q Topic with pre-joined datasets
        self._create_optimized_topic()

        # Grant optimized Topic permissions via Custom Resource
        self._grant_optimized_topic_permissions()

        # Outputs
        self._create_outputs()

        # The AwsCustomResource provider Lambda is created and versioned by aws-cdk-lib
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.stack_name}/AWS679f53fac002430cb0da5b7982bd2287/Resource",
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Runtime of the CDK-managed AwsCustomResource provider is set by aws-cdk-lib; it follows CDK upgrades.",
                }
            ],
        )

    def _create_custom_resource_log_group(self) -> None:
        """Log group for the shared AwsCustomResource Lambda.

        Without this the Lambda's log group never expires and survives ``cdk destroy``.
        """
        self.custom_resource_log_group = logs.LogGroup(
            self,
            "CustomResourceLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

    def _create_custom_resource_role(self) -> None:
        """Create IAM role for custom resources in this stack.

        This role is used for setting Q Topic permissions via the
        UpdateTopicPermissions API.
        """
        self.custom_resource_role = iam.Role(
            self,
            "TopicsCustomResourceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "TopicPermissionsPolicy": iam.PolicyDocument(
                    statements=[
                        # Write logs only to this stack's custom-resource log group
                        # (replaces the AWSLambdaBasicExecutionRole managed policy)
                        iam.PolicyStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=[self.custom_resource_log_group.log_group_arn],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "quicksight:UpdateTopicPermissions",
                                "quicksight:DescribeTopicPermissions",
                            ],
                            resources=[
                                f"arn:aws:quicksight:{self.region}:{self.account}:topic/conversational-analytics-cards-topic",
                                f"arn:aws:quicksight:{self.region}:{self.account}:topic/conversational-analytics-optimized-topic",
                            ],
                        ),
                    ]
                )
            },
        )

    def _get_dataset_arn(self, dataset_id: str) -> str:
        """Construct dataset ARN from dataset ID.

        Dataset IDs follow the pattern: conversational-analytics-<table_name> or conversational-analytics-<joined_name>
        """
        return f"arn:aws:quicksight:{self.region}:{self.account}:dataset/{dataset_id}"

    def _create_quicksight_topic(self) -> None:
        """Create QuickSight Q Topic for natural language queries.

        The Topic enables users to ask questions like:
        - "Show chargebacks from FastShop Online"
        - "What is average days to tokenize in Spain?"
        - "Best customer spending by category"
        """
        # Build DatasetMetadata for each table
        dataset_metadata_list = []
        for table_name, columns in QUICKSIGHT_TABLES.items():
            # Construct dataset ARN from known ID pattern
            dataset_id = f"conversational-analytics-{table_name.replace('_', '-')}"
            dataset_arn = self._get_dataset_arn(dataset_id)
            topic_columns = self._build_topic_columns(table_name, columns)

            dataset_metadata = quicksight.CfnTopic.DatasetMetadataProperty(
                dataset_arn=dataset_arn,
                dataset_name=f"{table_name.replace('_', ' ').title()}",
                dataset_description=self._get_table_description(table_name),
                columns=topic_columns,
            )
            dataset_metadata_list.append(dataset_metadata)

        # Custom instructions to help Q understand the data model
        custom_instructions_text = """This topic covers AnyCompany Bank's Cards domain data for credit/debit card operations across 8 European countries (ES, DE, UK, FR, IT, NL, PL, PT).

DATA MODEL RELATIONSHIPS:
- transactions links to cards (card_id), customers (customer_id), and merchants (merchant_id)
- chargebacks links to transactions (transaction_id)
- tokenizations links to customers (customer_id) and cards (card_id)
- cards links to customers (customer_id)

MEMBERSHIP TIERS:
- "standard" = free tier (50% of customers), synonyms: std, free account
- "plus" = plus tier
- "gold" = gold tier
- "metal" = premium tier (highest spending), 20% of customers
- "select" = select tier
- Stored in membership_tier column

CHARGEBACKS:
- "Unauthorized" chargebacks = fraud (cardholder didn't authorize)
- "Authorized" chargebacks = disputes (merchandise issues, etc.)
- Use chargeback_type column to filter

TOKENIZATION:
- days_to_tokenize = days from customer registration to adding card to digital wallet
- wallet_type: apple_pay, google_pay, samsung_pay

DELIVERY:
- Card delivery time = days from issue_date to delivery_date
- delivery_type: express or standard

SPECIAL CAMPAIGNS:
- campaign_code = 'XMAS_2025' identifies Christmas special edition cards

AMOUNTS:
- All monetary values (amount_cents, transaction_amount) are in cents. Divide by 100 for euros/currency display.

MERCHANT CATEGORIES (MCC):
- 4722 = Travel, 5812 = Restaurants
- 5411 = Groceries, 5541 = Gas
- 5944 = Jewelry, 5945 = Toys"""

        # Create the Topic
        self.topic = quicksight.CfnTopic(
            self,
            "QuickSightQTopic",
            aws_account_id=self.account,
            topic_id="conversational-analytics-cards-topic",
            name="Cards Domain",
            description="Natural language queries for AnyCompany Bank Cards domain data. Ask about transactions, chargebacks, tokenizations, cards, customers, and merchants.",
            data_sets=dataset_metadata_list,
            user_experience_version="NEW_READER_EXPERIENCE",
            custom_instructions=quicksight.CfnTopic.CustomInstructionsProperty(
                custom_instructions_string=custom_instructions_text,
            ),
        )

    def _build_topic_columns(
        self, table_name: str, columns: list[QuickSightColumn]
    ) -> list[quicksight.CfnTopic.TopicColumnProperty]:
        """Build TopicColumn definitions with synonyms for a table.

        Args:
            table_name: Name of the table (e.g., 'customers')
            columns: List of QuickSightColumn definitions from schema

        Returns:
            List of TopicColumnProperty objects with synonyms configured
        """
        topic_columns = []
        table_column_synonyms = COLUMN_SYNONYMS.get(table_name, {})
        table_cell_synonyms = CELL_VALUE_SYNONYMS.get(table_name, {})

        for col in columns:
            # Get column synonyms
            col_synonyms = table_column_synonyms.get(col.name, [])

            # Get cell value synonyms for this column
            cell_value_synonym_list = []
            col_cell_synonyms = table_cell_synonyms.get(col.name, {})

            # Add cell value synonyms from table-specific config
            for cell_value, synonyms in col_cell_synonyms.items():
                cell_value_synonym_list.append(
                    quicksight.CfnTopic.CellValueSynonymProperty(
                        cell_value=cell_value,
                        synonyms=synonyms,
                    )
                )

            # Add country synonyms for country columns
            if col.name == "country":
                for country_code, synonyms in COUNTRY_SYNONYMS.items():
                    cell_value_synonym_list.append(
                        quicksight.CfnTopic.CellValueSynonymProperty(
                            cell_value=country_code,
                            synonyms=synonyms,
                        )
                    )

            # Build SemanticType if specified
            semantic_type = None
            if col.semantic_type_name:
                semantic_type = quicksight.CfnTopic.SemanticTypeProperty(
                    type_name=col.semantic_type_name,
                )

            # Build the TopicColumn with enhanced configuration
            topic_column = quicksight.CfnTopic.TopicColumnProperty(
                column_name=col.name,
                column_friendly_name=self._format_column_name(col.name),
                column_description=col.description,
                column_data_role="DIMENSION" if col.is_dimension else "MEASURE",
                is_included_in_topic=True,
                column_synonyms=col_synonyms if col_synonyms else None,
                cell_value_synonyms=cell_value_synonym_list if cell_value_synonym_list else None,
                non_additive=col.non_additive if col.non_additive else None,
                # Enhanced Q Topic configuration
                semantic_type=semantic_type,
                time_granularity=col.time_granularity if col.time_granularity else None,
                aggregation=col.default_aggregation if col.default_aggregation else None,
                allowed_aggregations=col.allowed_aggregations if col.allowed_aggregations else None,
                disable_indexing=col.disable_indexing if col.disable_indexing else None,
            )
            topic_columns.append(topic_column)

        return topic_columns

    def _format_column_name(self, column_name: str) -> str:
        """Convert snake_case column name to Title Case friendly name."""
        return column_name.replace("_", " ").title()

    def _get_table_description(self, table_name: str) -> str:
        """Get a description for a table for the Topic."""
        descriptions = {
            "customers": "Customer profiles including membership tier, type (personal/business), and status.",
            "cards": "Card products with type, tier, network, delivery info, and campaign codes.",
            "transactions": "Individual card transactions with amounts, approval status, and merchant links.",
            "tokenizations": "Digital wallet provisioning events with timing metrics (days_to_tokenize).",
            "chargebacks": "Transaction disputes with type (unauthorized/authorized), reason codes, and resolution.",
            "merchants": "Merchant information with category codes (MCC), channel, and location.",
        }
        return descriptions.get(table_name, f"{table_name} data")

    def _grant_topic_permissions(self) -> None:
        """Grant permissions on Q Topic via Custom Resource.

        CfnTopic doesn't have a native permissions property, so we use
        AwsCustomResource to call the UpdateTopicPermissions API.
        """
        # Topic permissions must be provided as complete valid sets per AWS API.
        # Valid owner set includes all refresh schedule actions.
        topic_owner_actions = [
            "quicksight:DescribeTopic",
            "quicksight:DescribeTopicRefresh",
            "quicksight:ListTopicRefreshSchedules",
            "quicksight:DescribeTopicRefreshSchedule",
            "quicksight:DeleteTopic",
            "quicksight:UpdateTopic",
            "quicksight:CreateTopicRefreshSchedule",
            "quicksight:DeleteTopicRefreshSchedule",
            "quicksight:UpdateTopicRefreshSchedule",
            "quicksight:DescribeTopicPermissions",
            "quicksight:UpdateTopicPermissions",
        ]

        # Owner permissions for the deploying user, read-only for the group
        permissions = [
            {
                "Principal": self.quicksight_user_arn,
                "Actions": topic_owner_actions,
            },
            {
                "Principal": self.quicksight_group_arn,
                "Actions": TOPIC_READER_ACTIONS,
            },
        ]

        # Create custom resource to set permissions
        self.topic_permissions = cr.AwsCustomResource(
            self,
            "TopicPermissions",
            on_create=cr.AwsSdkCall(
                service="QuickSight",
                action="updateTopicPermissions",
                parameters={
                    "AwsAccountId": self.account,
                    "TopicId": "conversational-analytics-cards-topic",
                    "GrantPermissions": permissions,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "conversational-analytics-topic-permissions"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="QuickSight",
                action="updateTopicPermissions",
                parameters={
                    "AwsAccountId": self.account,
                    "TopicId": "conversational-analytics-cards-topic",
                    "GrantPermissions": permissions,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "conversational-analytics-topic-permissions"
                ),
            ),
            # No on_delete - permissions are deleted when Topic is deleted
            role=self.custom_resource_role,
            log_group=self.custom_resource_log_group,
        )

        # Ensure permissions are set after Topic is created
        self.topic_permissions.node.add_dependency(self.topic)

    # =========================================================================
    # OPTIMIZED Q TOPIC WITH PRE-JOINED DATASETS
    # =========================================================================

    def _create_optimized_topic(self) -> None:
        """Create optimized Q Topic with pre-joined datasets.

        This topic uses pre-joined datasets that enable answering
        cross-table questions like:
        - "What merchants do metal tier customers prefer?" (UC-3)
        - "Why did chargebacks increase last week?" (UC-2)
        """
        # Build DatasetMetadata for ALL joined datasets
        dataset_metadata_list = []
        for name, dataset_def in JOINED_DATASETS.items():
            # Construct dataset ARN from known ID pattern
            dataset_id = f"conversational-analytics-{name}"
            dataset_arn = self._get_dataset_arn(dataset_id)
            topic_columns = self._build_optimized_topic_columns(name, dataset_def)

            dataset_metadata = quicksight.CfnTopic.DatasetMetadataProperty(
                dataset_arn=dataset_arn,
                dataset_name=dataset_def.display_name,
                dataset_description=dataset_def.description,
                columns=topic_columns,
            )
            dataset_metadata_list.append(dataset_metadata)

        # Create the optimized Topic with custom instructions
        self.optimized_topic = quicksight.CfnTopic(
            self,
            "QuickSightOptimizedTopic",
            aws_account_id=self.account,
            topic_id="conversational-analytics-optimized-topic",
            name="Cards Domain (Optimized)",
            description="Natural language queries for AnyCompany Bank Cards domain with pre-joined data for complex analytics. Supports all 6 use cases.",
            data_sets=dataset_metadata_list,
            user_experience_version="NEW_READER_EXPERIENCE",
            custom_instructions=quicksight.CfnTopic.CustomInstructionsProperty(
                custom_instructions_string=OPTIMIZED_TOPIC_INSTRUCTIONS,
            ),
        )

    def _build_optimized_topic_columns(
        self, dataset_name: str, dataset_def
    ) -> list[quicksight.CfnTopic.TopicColumnProperty]:
        """Build TopicColumn definitions with synonyms for a joined dataset.

        Args:
            dataset_name: Name of the joined dataset (e.g., 'spending-analysis')
            dataset_def: JoinedDatasetDefinition with column definitions

        Returns:
            List of TopicColumnProperty objects with synonyms configured
        """
        topic_columns = []
        dataset_column_synonyms = JOINED_COLUMN_SYNONYMS.get(dataset_name, {})
        dataset_cell_synonyms = JOINED_CELL_VALUE_SYNONYMS.get(dataset_name, {})

        for col in dataset_def.columns:
            # Get column synonyms
            col_synonyms = dataset_column_synonyms.get(col.name, [])

            # Get cell value synonyms for this column
            cell_value_synonym_list = []
            col_cell_synonyms = dataset_cell_synonyms.get(col.name, {})

            # Add cell value synonyms from dataset-specific config
            for cell_value, synonyms in col_cell_synonyms.items():
                cell_value_synonym_list.append(
                    quicksight.CfnTopic.CellValueSynonymProperty(
                        cell_value=cell_value,
                        synonyms=synonyms,
                    )
                )

            # Add country synonyms for country columns
            if col.name in ("country", "customer_country", "merchant_country"):
                for country_code, synonyms in JOINED_COUNTRY_SYNONYMS.items():
                    cell_value_synonym_list.append(
                        quicksight.CfnTopic.CellValueSynonymProperty(
                            cell_value=country_code,
                            synonyms=synonyms,
                        )
                    )

            # Build SemanticType if specified
            semantic_type = None
            if col.semantic_type_name:
                semantic_type = quicksight.CfnTopic.SemanticTypeProperty(
                    type_name=col.semantic_type_name,
                )

            # Build the TopicColumn with full configuration
            topic_column = quicksight.CfnTopic.TopicColumnProperty(
                column_name=col.name,
                column_friendly_name=self._format_column_name(col.name),
                column_description=col.description,
                column_data_role="DIMENSION" if col.is_dimension else "MEASURE",
                is_included_in_topic=True,
                column_synonyms=col_synonyms if col_synonyms else None,
                cell_value_synonyms=cell_value_synonym_list if cell_value_synonym_list else None,
                non_additive=col.non_additive if col.non_additive else None,
                semantic_type=semantic_type,
                time_granularity=col.time_granularity if col.time_granularity else None,
                aggregation=col.default_aggregation if col.default_aggregation else None,
                allowed_aggregations=col.allowed_aggregations if col.allowed_aggregations else None,
                disable_indexing=col.disable_indexing if col.disable_indexing else None,
            )
            topic_columns.append(topic_column)

        return topic_columns

    def _grant_optimized_topic_permissions(self) -> None:
        """Grant permissions on optimized Q Topic via Custom Resource."""
        # Topic permissions must be provided as complete valid sets per AWS API.
        topic_owner_actions = [
            "quicksight:DescribeTopic",
            "quicksight:DescribeTopicRefresh",
            "quicksight:ListTopicRefreshSchedules",
            "quicksight:DescribeTopicRefreshSchedule",
            "quicksight:DeleteTopic",
            "quicksight:UpdateTopic",
            "quicksight:CreateTopicRefreshSchedule",
            "quicksight:DeleteTopicRefreshSchedule",
            "quicksight:UpdateTopicRefreshSchedule",
            "quicksight:DescribeTopicPermissions",
            "quicksight:UpdateTopicPermissions",
        ]

        # Owner permissions for the deploying user, read-only for the group
        permissions = [
            {
                "Principal": self.quicksight_user_arn,
                "Actions": topic_owner_actions,
            },
            {
                "Principal": self.quicksight_group_arn,
                "Actions": TOPIC_READER_ACTIONS,
            },
        ]

        # Create custom resource to set permissions
        self.optimized_topic_permissions = cr.AwsCustomResource(
            self,
            "OptimizedTopicPermissions",
            on_create=cr.AwsSdkCall(
                service="QuickSight",
                action="updateTopicPermissions",
                parameters={
                    "AwsAccountId": self.account,
                    "TopicId": "conversational-analytics-optimized-topic",
                    "GrantPermissions": permissions,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "conversational-analytics-optimized-topic-permissions"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="QuickSight",
                action="updateTopicPermissions",
                parameters={
                    "AwsAccountId": self.account,
                    "TopicId": "conversational-analytics-optimized-topic",
                    "GrantPermissions": permissions,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "conversational-analytics-optimized-topic-permissions"
                ),
            ),
            # No on_delete - permissions are deleted when Topic is deleted
            role=self.custom_resource_role,
            log_group=self.custom_resource_log_group,
        )

        # Ensure permissions are set after Topic is created
        self.optimized_topic_permissions.node.add_dependency(self.optimized_topic)

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        # Construct ARN manually
        topic_arn = f"arn:aws:quicksight:{self.region}:{self.account}:topic/conversational-analytics-cards-topic"
        cdk.CfnOutput(
            self,
            "QuickSightTopicArn",
            value=topic_arn,
            description="QuickSight Q Topic ARN (raw tables)",
            export_name="ConversationalAnalytics-QuickSightTopic",
        )

        optimized_topic_arn = f"arn:aws:quicksight:{self.region}:{self.account}:topic/conversational-analytics-optimized-topic"
        cdk.CfnOutput(
            self,
            "QuickSightOptimizedTopicArn",
            value=optimized_topic_arn,
            description="QuickSight Q Topic ARN (optimized with pre-joined datasets)",
            export_name="ConversationalAnalytics-QuickSightOptimizedTopic",
        )
