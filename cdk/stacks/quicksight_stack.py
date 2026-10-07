# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""QuickSight Stack - DataSource and DataSets.

This stack creates QuickSight resources that reference the Glue tables:
- QuickSight Group for demo users
- DataSource connected to Athena
- DataSets for raw tables (6 tables)
- Pre-joined DataSets for analytics (5 datasets)
- S3 access policy for QuickSight service role

Q Topics are created in a separate stack (ConversationalAnalytics-QuickSight-Topics) to allow
independent iteration. When Q Topic refresh fails, only that stack rolls back
while datasets remain intact.

Deployment:
    uv run cdk deploy ConversationalAnalytics-QuickSight

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import json
import sys
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    Fn,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_quicksight as quicksight,
)
from aws_cdk import (
    custom_resources as cr,
)
from cdk_nag import NagSuppressions
from constructs import Construct

# Add src to path for schema imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from conversational_analytics.joined_datasets import JOINED_DATASETS, JoinedDatasetDefinition
from conversational_analytics.schema_definitions import QUICKSIGHT_TABLES

# Read-only permission sets for the conversational-analytics-demo group. Only the deploying user
# (QUICKSIGHT_USER_ARN) gets owner actions such as update, delete and re-share.
DATASOURCE_READER_ACTIONS = [
    "quicksight:DescribeDataSource",
    "quicksight:DescribeDataSourcePermissions",
    "quicksight:PassDataSource",
]
DATASET_READER_ACTIONS = [
    "quicksight:DescribeDataSet",
    "quicksight:DescribeDataSetPermissions",
    "quicksight:PassDataSet",
    "quicksight:DescribeIngestion",
    "quicksight:ListIngestions",
]


class QuickSightStack(cdk.Stack):
    """QuickSight resources stack for Conversational Analytics - DataSource and DataSets only.

    Creates:
    - QuickSight Group for demo users
    - DataSource connected to Athena
    - DataSets for each of the 6 raw tables
    - Pre-joined DataSets for analytics (5 datasets)
    - S3 access policy for QuickSight service role

    Q Topics are created in a separate stack (QuickSightTopicsStack) to allow
    independent iteration without risking dataset rollbacks.

    Prerequisites:
    - InfraStack deployed (S3, Glue DB, Athena workgroup)
    - GlueTablesStack deployed (table definitions)
    - Data loaded into S3 and partitions repaired
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        quicksight_user_arn: str,
        quicksight_namespace: str = "default",
        athena_workgroup_name: str | None = None,
        data_lake_bucket_name: str | None = None,
        additional_member_usernames: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.quicksight_user_arn = quicksight_user_arn
        self.quicksight_namespace = quicksight_namespace
        self.additional_member_usernames = additional_member_usernames or []

        # Import from InfraStack or use provided values
        self.athena_workgroup_name = athena_workgroup_name or Fn.import_value(
            "ConversationalAnalytics-AthenaWorkgroup"
        )
        self.data_lake_bucket_name = data_lake_bucket_name or Fn.import_value(
            "ConversationalAnalytics-DataLakeBucket"
        )

        # Create shared role for ALL custom resources
        # CRITICAL: CDK shares a single Lambda for all AwsCustomResource instances.
        # Using different roles causes conflicts. All permissions must be in one role.
        self._create_custom_resource_log_group()
        self._create_shared_custom_resource_role()

        # Grant QuickSight service role access to S3 datalake
        self._grant_quicksight_service_role_s3_access()

        # Create QuickSight group first (permissions depend on it)
        self._create_quicksight_group()

        # Add additional members to the group
        for username in self.additional_member_usernames:
            self._add_group_member(username)

        # Create DataSource
        self._create_quicksight_datasource()

        # Create DataSets for raw tables
        self._create_quicksight_datasets()

        # Create pre-joined datasets for optimized Q Topic
        self._create_joined_datasets()

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

    def _create_shared_custom_resource_role(self) -> None:
        """Create a shared IAM role for ALL custom resources in this stack.

        CRITICAL: CDK's AwsCustomResource shares a single Lambda function across
        all custom resources in a stack. If you assign different roles to different
        custom resources, they conflict because the Lambda can only have one
        execution role at a time. This causes permission errors when CloudFormation
        invokes the Lambda with the wrong role.

        Solution: Create ONE role with ALL permissions needed by ALL custom resources,
        and use this role for every AwsCustomResource in the stack.

        Note: Topic permissions are in the QuickSightTopicsStack's custom resource role.
        """
        self.group_name = "conversational-analytics-demo"

        self.custom_resource_role = iam.Role(
            self,
            "CustomResourceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "AllCustomResourcePermissions": iam.PolicyDocument(
                    statements=[
                        # Write logs only to this stack's custom-resource log group
                        # (replaces the AWSLambdaBasicExecutionRole managed policy)
                        iam.PolicyStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=[self.custom_resource_log_group.log_group_arn],
                        ),
                        # IAM permissions for S3 policy on QuickSight service role
                        iam.PolicyStatement(
                            actions=[
                                "iam:PutRolePolicy",
                                "iam:DeleteRolePolicy",
                            ],
                            resources=[
                                f"arn:aws:iam::{self.account}:role/service-role/aws-quicksight-service-role-v0",
                            ],
                        ),
                        # QuickSight Group operations
                        iam.PolicyStatement(
                            actions=[
                                "quicksight:CreateGroup",
                                "quicksight:DeleteGroup",
                                "quicksight:DescribeGroup",
                            ],
                            resources=[
                                f"arn:aws:quicksight:{self.region}:{self.account}:group/{self.quicksight_namespace}/{self.group_name}",
                            ],
                        ),
                        # QuickSight Group membership operations
                        iam.PolicyStatement(
                            actions=[
                                "quicksight:CreateGroupMembership",
                                "quicksight:DeleteGroupMembership",
                                "quicksight:DescribeGroupMembership",
                                "quicksight:ListGroupMemberships",
                            ],
                            resources=[
                                f"arn:aws:quicksight:{self.region}:{self.account}:group/{self.quicksight_namespace}/{self.group_name}",
                            ],
                        ),
                    ]
                )
            },
        )

    def _grant_quicksight_service_role_s3_access(self) -> None:
        """Grant QuickSight service role access to the S3 datalake bucket.

        The AWSQuicksightAthenaAccess managed policy only grants S3 access to
        buckets matching 'aws-athena-query-results-*'. We need to add an inline
        policy to the QuickSight service role to grant access to our datalake bucket.

        Uses AwsCustomResource to add an inline policy to the existing
        aws-quicksight-service-role-v0 role.
        """
        # Policy document granting S3 read access to the datalake bucket
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:GetBucketLocation",
                        "s3:ListBucket",
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self.data_lake_bucket_name}",
                        f"arn:aws:s3:::{self.data_lake_bucket_name}/*",
                    ],
                }
            ],
        }

        # Add inline policy to QuickSight service role
        # Uses the shared custom resource role
        self.quicksight_s3_policy = cr.AwsCustomResource(
            self,
            "QuickSightServiceRoleS3Policy",
            on_create=cr.AwsSdkCall(
                service="IAM",
                action="putRolePolicy",
                parameters={
                    "RoleName": "aws-quicksight-service-role-v0",
                    "PolicyName": "ConversationalAnalyticsDataLakeAccess",
                    "PolicyDocument": json.dumps(policy_document),
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "qs-service-role-conversational-analytics-s3-policy"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="IAM",
                action="putRolePolicy",
                parameters={
                    "RoleName": "aws-quicksight-service-role-v0",
                    "PolicyName": "ConversationalAnalyticsDataLakeAccess",
                    "PolicyDocument": json.dumps(policy_document),
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "qs-service-role-conversational-analytics-s3-policy"
                ),
            ),
            on_delete=cr.AwsSdkCall(
                service="IAM",
                action="deleteRolePolicy",
                parameters={
                    "RoleName": "aws-quicksight-service-role-v0",
                    "PolicyName": "ConversationalAnalyticsDataLakeAccess",
                },
            ),
            role=self.custom_resource_role,
            log_group=self.custom_resource_log_group,
        )

    def _create_quicksight_group(self) -> None:
        """Create QuickSight group and add user via Custom Resource.

        CloudFormation doesn't support AWS::QuickSight::Group natively,
        so we use AwsCustomResource to call the QuickSight API directly.

        Uses the shared custom resource role created in _create_shared_custom_resource_role().
        """
        # Extract username from ARN
        # Format: arn:aws:quicksight:region:account:user/namespace/username
        user_name = self.quicksight_user_arn.split(":user/")[-1].split("/", 1)[-1]

        # Create QuickSight Group using shared role
        self.quicksight_group_resource = cr.AwsCustomResource(
            self,
            "QuickSightGroup",
            on_create=cr.AwsSdkCall(
                service="QuickSight",
                action="createGroup",
                parameters={
                    "AwsAccountId": self.account,
                    "Namespace": self.quicksight_namespace,
                    "GroupName": self.group_name,
                    "Description": "demo users with full access to datasets and topics",
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"qs-group-{self.group_name}"
                ),
            ),
            on_delete=cr.AwsSdkCall(
                service="QuickSight",
                action="deleteGroup",
                parameters={
                    "AwsAccountId": self.account,
                    "Namespace": self.quicksight_namespace,
                    "GroupName": self.group_name,
                },
            ),
            role=self.custom_resource_role,
            log_group=self.custom_resource_log_group,
        )

        # Store group ARN for permissions
        self.quicksight_group_arn = f"arn:aws:quicksight:{self.region}:{self.account}:group/{self.quicksight_namespace}/{self.group_name}"

        # Add user to group using the shared role
        create_membership = cr.AwsCustomResource(
            self,
            "QuickSightGroupMembership",
            on_create=cr.AwsSdkCall(
                service="QuickSight",
                action="createGroupMembership",
                parameters={
                    "AwsAccountId": self.account,
                    "Namespace": self.quicksight_namespace,
                    "GroupName": self.group_name,
                    "MemberName": user_name,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"qs-membership-{self.group_name}-{user_name}"
                ),
            ),
            on_delete=cr.AwsSdkCall(
                service="QuickSight",
                action="deleteGroupMembership",
                parameters={
                    "AwsAccountId": self.account,
                    "Namespace": self.quicksight_namespace,
                    "GroupName": self.group_name,
                    "MemberName": user_name,
                },
            ),
            role=self.custom_resource_role,
            log_group=self.custom_resource_log_group,
        )

        # Ensure membership is created after group
        create_membership.node.add_dependency(self.quicksight_group_resource)

    def _add_group_member(self, username: str) -> None:
        """Add an additional user to the conversational-analytics-demo group.

        Args:
            username: QuickSight username (e.g. 'user@example.com' for native
                      QuickSight users, or 'namespace/user@example.com' for IAM-federated)
        """
        # Use a safe construct ID derived from the username
        safe_id = username.replace("@", "-at-").replace(".", "-")
        membership = cr.AwsCustomResource(
            self,
            f"GroupMembership-{safe_id}",
            on_create=cr.AwsSdkCall(
                service="QuickSight",
                action="createGroupMembership",
                parameters={
                    "AwsAccountId": self.account,
                    "Namespace": self.quicksight_namespace,
                    "GroupName": self.group_name,
                    "MemberName": username,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"qs-membership-{self.group_name}-{safe_id}"
                ),
            ),
            on_delete=cr.AwsSdkCall(
                service="QuickSight",
                action="deleteGroupMembership",
                parameters={
                    "AwsAccountId": self.account,
                    "Namespace": self.quicksight_namespace,
                    "GroupName": self.group_name,
                    "MemberName": username,
                },
            ),
            role=self.custom_resource_role,
            log_group=self.custom_resource_log_group,
        )
        membership.node.add_dependency(self.quicksight_group_resource)

    def _create_quicksight_datasource(self) -> None:
        """Create QuickSight DataSource pointing to Athena."""
        # Full owner permissions for DataSource
        datasource_owner_actions = [
            "quicksight:DescribeDataSource",
            "quicksight:DescribeDataSourcePermissions",
            "quicksight:PassDataSource",
            "quicksight:UpdateDataSource",
            "quicksight:DeleteDataSource",
            "quicksight:UpdateDataSourcePermissions",
        ]

        # Owner permissions for the deploying user, read-only for the group
        permissions = [
            quicksight.CfnDataSource.ResourcePermissionProperty(
                principal=self.quicksight_user_arn,
                actions=datasource_owner_actions,
            ),
            quicksight.CfnDataSource.ResourcePermissionProperty(
                principal=self.quicksight_group_arn,
                actions=DATASOURCE_READER_ACTIONS,
            ),
        ]

        self.datasource = quicksight.CfnDataSource(
            self,
            "QuickSightDataSource",
            aws_account_id=self.account,
            data_source_id="conversational-analytics-athena-datasource",
            name="Conversational Analytics Athena",
            type="ATHENA",
            data_source_parameters=quicksight.CfnDataSource.DataSourceParametersProperty(
                athena_parameters=quicksight.CfnDataSource.AthenaParametersProperty(
                    work_group="conversational-analytics-workgroup",
                ),
            ),
            permissions=permissions,
            ssl_properties=quicksight.CfnDataSource.SslPropertiesProperty(
                disable_ssl=False,
            ),
        )

        # Add dependency on QuickSight group
        self.datasource.node.add_dependency(self.quicksight_group_resource)

    def _create_quicksight_datasets(self) -> None:
        """Create QuickSight DataSets for each table.

        CRITICAL: Physical table map keys must match pattern [0-9a-zA-Z-]*
        Use HYPHENS instead of underscores!
        """
        self.datasets = {}

        for table_name, columns in QUICKSIGHT_TABLES.items():
            dataset = self._create_quicksight_dataset(table_name, columns)
            self.datasets[table_name] = dataset

    def _create_quicksight_dataset(
        self, table_name: str, columns: list
    ) -> quicksight.CfnDataSet:
        """Create a single QuickSight DataSet.

        Args:
            table_name: Name of the table (e.g., 'card_transactions')
            columns: List of QuickSightColumn definitions
        """
        # CRITICAL: Convert underscores to hyphens for physical table map key
        # QuickSight requires pattern [0-9a-zA-Z-]* (NO UNDERSCORES!)
        physical_key = table_name.replace("_", "-") + "-physical"
        dataset_id = f"conversational-analytics-{table_name.replace('_', '-')}"

        # Build input columns
        # Note: QuickSight doesn't have a DATE type, so we map DATE -> DATETIME
        # The Athena/Glue tables use the actual 'date' type for proper Parquet compatibility
        qs_type_mapping = {"DATE": "DATETIME"}
        input_columns = [
            quicksight.CfnDataSet.InputColumnProperty(
                name=col.name,
                type=qs_type_mapping.get(col.qs_type, col.qs_type),
            )
            for col in columns
        ]

        # Full owner permissions for DataSet
        dataset_owner_actions = [
            # Reader permissions
            "quicksight:DescribeDataSet",
            "quicksight:DescribeDataSetPermissions",
            "quicksight:PassDataSet",
            "quicksight:DescribeIngestion",
            "quicksight:ListIngestions",
            # Owner permissions
            "quicksight:UpdateDataSet",
            "quicksight:DeleteDataSet",
            "quicksight:CreateIngestion",
            "quicksight:CancelIngestion",
            "quicksight:UpdateDataSetPermissions",
        ]

        # Owner permissions for the deploying user, read-only for the group
        permissions = [
            quicksight.CfnDataSet.ResourcePermissionProperty(
                principal=self.quicksight_user_arn,
                actions=dataset_owner_actions,
            ),
            quicksight.CfnDataSet.ResourcePermissionProperty(
                principal=self.quicksight_group_arn,
                actions=DATASET_READER_ACTIONS,
            ),
        ]

        # Create dataset
        dataset = quicksight.CfnDataSet(
            self,
            f"DataSet{table_name.title().replace('_', '')}",
            aws_account_id=self.account,
            data_set_id=dataset_id,
            name=f"{table_name.replace('_', ' ').title()}",
            import_mode="DIRECT_QUERY",  # Query directly from Athena
            physical_table_map={
                physical_key: quicksight.CfnDataSet.PhysicalTableProperty(
                    relational_table=quicksight.CfnDataSet.RelationalTableProperty(
                        data_source_arn=self.datasource.attr_arn,
                        catalog="AwsDataCatalog",
                        schema="conversational_analytics",
                        name=table_name,
                        input_columns=input_columns,
                    ),
                ),
            },
            permissions=permissions,
        )

        # Add dependency on datasource
        dataset.add_resource_dependency(self.datasource)

        return dataset

    # =========================================================================
    # PRE-JOINED DATASETS FOR OPTIMIZED Q TOPIC
    # =========================================================================

    def _create_joined_datasets(self) -> None:
        """Create pre-joined QuickSight DataSets using Custom SQL.

        These datasets combine multiple tables via JOINs to enable Q Topic
        to answer cross-table questions without dynamic joining.
        """
        self.joined_datasets: dict[str, quicksight.CfnDataSet] = {}

        for name, dataset_def in JOINED_DATASETS.items():
            dataset = self._create_custom_sql_dataset(dataset_def)
            self.joined_datasets[name] = dataset

    def _create_custom_sql_dataset(
        self, dataset_def: JoinedDatasetDefinition
    ) -> quicksight.CfnDataSet:
        """Create a QuickSight DataSet using Custom SQL.

        Args:
            dataset_def: JoinedDatasetDefinition with SQL and column specs

        Returns:
            CfnDataSet resource
        """
        # CRITICAL: Physical table map key must use hyphens, not underscores
        physical_key = dataset_def.name + "-physical"
        dataset_id = f"conversational-analytics-{dataset_def.name}"

        # Build input columns from the dataset definition
        # Map DATE -> DATETIME as QuickSight doesn't have DATE type
        qs_type_mapping = {"DATE": "DATETIME"}
        input_columns = [
            quicksight.CfnDataSet.InputColumnProperty(
                name=col.name,
                type=qs_type_mapping.get(col.qs_type, col.qs_type),
            )
            for col in dataset_def.columns
        ]

        # Full owner permissions for DataSet
        dataset_owner_actions = [
            # Reader permissions
            "quicksight:DescribeDataSet",
            "quicksight:DescribeDataSetPermissions",
            "quicksight:PassDataSet",
            "quicksight:DescribeIngestion",
            "quicksight:ListIngestions",
            # Owner permissions
            "quicksight:UpdateDataSet",
            "quicksight:DeleteDataSet",
            "quicksight:CreateIngestion",
            "quicksight:CancelIngestion",
            "quicksight:UpdateDataSetPermissions",
        ]

        # Owner permissions for the deploying user, read-only for the group
        permissions = [
            quicksight.CfnDataSet.ResourcePermissionProperty(
                principal=self.quicksight_user_arn,
                actions=dataset_owner_actions,
            ),
            quicksight.CfnDataSet.ResourcePermissionProperty(
                principal=self.quicksight_group_arn,
                actions=DATASET_READER_ACTIONS,
            ),
        ]

        # Create dataset with Custom SQL
        # Convert name like "spending-analysis" to "JoinedDataSetSpendingAnalysis"
        construct_id = f"JoinedDataSet{''.join(word.title() for word in dataset_def.name.split('-'))}"

        dataset = quicksight.CfnDataSet(
            self,
            construct_id,
            aws_account_id=self.account,
            data_set_id=dataset_id,
            name=dataset_def.display_name,
            import_mode="DIRECT_QUERY",  # Query directly from Athena
            physical_table_map={
                physical_key: quicksight.CfnDataSet.PhysicalTableProperty(
                    custom_sql=quicksight.CfnDataSet.CustomSqlProperty(
                        data_source_arn=self.datasource.attr_arn,
                        name=dataset_def.name,
                        sql_query=dataset_def.sql,
                        columns=input_columns,
                    ),
                ),
            },
            permissions=permissions,
        )

        # Add dependency on datasource
        dataset.add_resource_dependency(self.datasource)

        return dataset

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        cdk.CfnOutput(
            self,
            "QuickSightDataSourceArn",
            value=self.datasource.attr_arn,
            description="QuickSight DataSource ARN",
            export_name="ConversationalAnalytics-QuickSightDataSource",
        )

        cdk.CfnOutput(
            self,
            "QuickSightGroupArn",
            value=self.quicksight_group_arn,
            description="QuickSight demo group ARN",
            export_name="ConversationalAnalytics-QuickSightGroup",
        )

        cdk.CfnOutput(
            self,
            "DataSetCount",
            value=str(len(self.datasets)),
            description="Number of raw QuickSight DataSets created",
        )

        cdk.CfnOutput(
            self,
            "JoinedDataSetCount",
            value=str(len(self.joined_datasets)),
            description="Number of pre-joined QuickSight DataSets created",
        )
