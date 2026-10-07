# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Infrastructure Stack - Core data platform resources.

This stack creates the foundational infrastructure that changes infrequently:
- S3 buckets for data lake and Athena results
- Glue database
- Athena workgroup
- IAM roles

This stack is deployed ONCE and rarely needs updates, enabling faster
iteration on the QuickSight stack which references these resources.

Deployment:
    uv run cdk deploy ConversationalAnalytics-Infra

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from typing import cast

import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
)
from aws_cdk import (
    aws_athena as athena,
)
from aws_cdk import (
    aws_glue as glue,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_s3 as s3,
)
from cdk_nag import NagSuppressions
from constructs import Construct


class InfraStack(cdk.Stack):
    """Infrastructure stack with S3, Glue database, and Athena workgroup.

    This stack exports its resource ARNs for use by dependent stacks.
    Separating infrastructure from QuickSight enables faster iteration
    since infrastructure changes are rare.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        s3_bucket_prefix: str,
        enable_quicksight_bucket_policy: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.s3_bucket_prefix = s3_bucket_prefix

        # Create infrastructure
        self._create_s3_buckets()
        self._create_glue_database()
        self._create_athena_workgroup()

        # Add bucket policies for QuickSight if enabled
        if enable_quicksight_bucket_policy:
            self._grant_quicksight_s3_access()

        self._use_boolean_secure_transport()

        # Export values for dependent stacks
        self._create_exports()

    def _use_boolean_secure_transport(self) -> None:
        """Write the enforce_ssl condition as a boolean instead of the string "false".

        IAM treats both the same, but the cfn-guard S3_BUCKET_SSL_REQUESTS_ONLY rule
        only matches the boolean. The deny statement from enforce_ssl is statement 0.
        """
        for bucket in (self.access_logs_bucket, self.data_lake_bucket, self.athena_results_bucket):
            if bucket.policy is None:
                raise ValueError(f"{bucket.node.id} has no bucket policy; enforce_ssl should create one")
            cast(s3.CfnBucketPolicy, bucket.policy.node.default_child).add_property_override(
                "PolicyDocument.Statement.0.Condition.Bool.aws:SecureTransport", False
            )

    def _create_s3_buckets(self) -> None:
        """Create S3 buckets for data lake and Athena results, plus an access-logs bucket."""
        # Server access logs for the data lake and Athena results buckets
        self.access_logs_bucket = s3.Bucket(
            self,
            "AccessLogsBucket",
            bucket_name=f"{self.s3_bucket_prefix}-logs-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireAccessLogs",
                    expiration=cdk.Duration.days(30),
                ),
                s3.LifecycleRule(
                    id="ExpireNoncurrentVersions",
                    noncurrent_version_expiration=cdk.Duration.days(1),
                ),
            ],
        )
        NagSuppressions.add_resource_suppressions(
            self.access_logs_bucket,
            [
                {
                    "id": "AwsSolutions-S1",
                    "reason": "This is the access-logs target bucket; logging it to itself would loop.",
                }
            ],
        )
        # Same justification for checkov and cfn-guard, which read template metadata
        access_logs_cfn = cast(s3.CfnBucket, self.access_logs_bucket.node.default_child)
        access_logs_cfn.add_metadata(
            "checkov",
            {"skip": [{"id": "CKV_AWS_18", "comment": "Access-logs target bucket; logging it to itself would loop."}]},
        )
        access_logs_cfn.add_metadata(
            "guard",
            {"SuppressedRules": ["S3_BUCKET_LOGGING_ENABLED"]},
        )

        # Data lake bucket for Parquet files
        self.data_lake_bucket = s3.Bucket(
            self,
            "DataLakeBucket",
            bucket_name=f"{self.s3_bucket_prefix}-{self.account}-{self.region}",
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="datalake/",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireNoncurrentVersions",
                    noncurrent_version_expiration=cdk.Duration.days(1),
                ),
            ],
        )

        # Athena results bucket
        # CRITICAL: Bucket name matches 'aws-athena-query-results-*' pattern
        # This works with AWSQuicksightAthenaAccess managed policy
        self.athena_results_bucket = s3.Bucket(
            self,
            "AthenaResultsBucket",
            bucket_name=f"aws-athena-query-results-analytics-{self.account}-{self.region}",
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="athena-results/",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CleanupQueryResults",
                    expiration=cdk.Duration.days(30),
                ),
                s3.LifecycleRule(
                    id="ExpireNoncurrentVersions",
                    noncurrent_version_expiration=cdk.Duration.days(1),
                ),
            ],
        )

    def _grant_quicksight_s3_access(self) -> None:
        """Grant QuickSight service principal access to S3 buckets.

        QuickSight needs:
        1. Read access to the data lake bucket (to read Parquet files via Athena)
        2. Read/Write access to the Athena results bucket (to store query results)

        NOTE: Although the Athena results bucket name matches 'aws-athena-query-results-*',
        explicit bucket policies ensure reliable access without depending solely on
        the AWSQuicksightAthenaAccess managed policy.
        """
        quicksight_principal = iam.ServicePrincipal("quicksight.amazonaws.com")

        # Grant QuickSight read access to the data lake bucket
        self.data_lake_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowQuickSightReadDataLake",
                effect=iam.Effect.ALLOW,
                principals=[quicksight_principal],
                actions=[
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                resources=[
                    self.data_lake_bucket.bucket_arn,
                    self.data_lake_bucket.arn_for_objects("*"),
                ],
                conditions={
                    "StringEquals": {
                        "aws:SourceAccount": self.account,
                    }
                },
            )
        )

        # Grant QuickSight read/write access to the Athena results bucket.
        # aws:SourceAccount prevents other accounts' QuickSight from using this
        # bucket (confused deputy).
        self.athena_results_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowQuickSightAthenaResults",
                effect=iam.Effect.ALLOW,
                principals=[quicksight_principal],
                actions=[
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:ListBucketMultipartUploads",
                    "s3:ListMultipartUploadParts",
                    "s3:AbortMultipartUpload",
                ],
                resources=[
                    self.athena_results_bucket.bucket_arn,
                    self.athena_results_bucket.arn_for_objects("*"),
                ],
                conditions={
                    "StringEquals": {
                        "aws:SourceAccount": self.account,
                    }
                },
            )
        )

    def _create_glue_database(self) -> None:
        """Create Glue database for Conversational Analytics tables."""
        self.glue_database = glue.CfnDatabase(
            self,
            "GlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="conversational_analytics",
                description="demonstration data platform for QuickSight Q",
            ),
        )

    def _create_athena_workgroup(self) -> None:
        """Create Athena workgroup for Conversational Analytics queries."""
        self.athena_workgroup = athena.CfnWorkGroup(
            self,
            "AthenaWorkgroup",
            name="conversational-analytics-workgroup",
            description="Workgroup for Conversational Analytics queries",
            state="ENABLED",
            recursive_delete_option=True,
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{self.athena_results_bucket.bucket_name}/query-results/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3",
                    ),
                ),
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=True,
                bytes_scanned_cutoff_per_query=10 * 1024 * 1024 * 1024,  # 10 GB
                engine_version=athena.CfnWorkGroup.EngineVersionProperty(
                    selected_engine_version="Athena engine version 3",
                ),
            ),
        )

        # Ensure workgroup is created after the results bucket
        self.athena_workgroup.node.add_dependency(self.athena_results_bucket)

    def _create_exports(self) -> None:
        """Export values for dependent stacks."""
        CfnOutput(
            self,
            "DataLakeBucketName",
            value=self.data_lake_bucket.bucket_name,
            description="S3 bucket for data lake Parquet files",
            export_name="ConversationalAnalytics-DataLakeBucket",
        )

        CfnOutput(
            self,
            "DataLakeBucketArn",
            value=self.data_lake_bucket.bucket_arn,
            description="S3 bucket ARN for data lake",
            export_name="ConversationalAnalytics-DataLakeBucketArn",
        )

        CfnOutput(
            self,
            "AthenaResultsBucketName",
            value=self.athena_results_bucket.bucket_name,
            description="S3 bucket for Athena query results",
            export_name="ConversationalAnalytics-AthenaResultsBucket",
        )

        CfnOutput(
            self,
            "GlueDatabaseName",
            value="conversational_analytics",
            description="Glue database name",
            export_name="ConversationalAnalytics-GlueDatabase",
        )

        CfnOutput(
            self,
            "AthenaWorkgroupName",
            value="conversational-analytics-workgroup",
            description="Athena workgroup name",
            export_name="ConversationalAnalytics-AthenaWorkgroup",
        )

        CfnOutput(
            self,
            "DataLakeS3Path",
            value=f"s3://{self.data_lake_bucket.bucket_name}/",
            description="S3 path for uploading data",
            export_name="ConversationalAnalytics-DataLakeS3Path",
        )
