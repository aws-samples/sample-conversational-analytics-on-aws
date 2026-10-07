#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CDK entry point for Conversational Analytics data platform.

Stack Architecture:
- ConversationalAnalytics-Infra: S3 buckets, Glue database, Athena workgroup (stateful, rarely changes)
- ConversationalAnalytics-GlueTables: Glue table definitions (can iterate freely)
- ConversationalAnalytics-QuickSight: DataSource, DataSets, Group (stable, rarely fails)
- ConversationalAnalytics-QuickSight-Topics: Q Topics (can fail independently during refresh)
- ConversationalAnalytics-QuickSight-Analysis: Dashboards and visualizations with ML anomaly detection

The Topics stack is separated from the DataSets stack to allow independent iteration.
When Q Topic refresh fails, only the Topics stack rolls back while datasets remain intact.

Deployment Order:
    # Phase 1: Infrastructure (S3, Glue DB, Athena Workgroup)
    uv run cdk deploy ConversationalAnalytics-Infra

    # Phase 2: Data Pipeline (run scripts)
    uv run python scripts/generate_data.py
    uv run python scripts/upload_to_s3.py
    uv run python scripts/create_tables.py

    # Phase 3: Glue Tables (after data is uploaded)
    uv run cdk deploy ConversationalAnalytics-GlueTables

    # Phase 4: QuickSight DataSets (after tables are created with data)
    uv run cdk deploy ConversationalAnalytics-QuickSight

    # Phase 5: QuickSight Topics (after datasets are created)
    uv run cdk deploy ConversationalAnalytics-QuickSight-Topics

    # Phase 6: QuickSight Analysis (optional - for dashboards)
    uv run cdk deploy ConversationalAnalytics-QuickSight-Analysis

    # Deploy all at once (after data is ready):
    uv run cdk deploy --all

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import getpass
import os
import sys
from pathlib import Path

# Add project root and cdk directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from cdk.stacks.glue_tables_stack import GlueTablesStack
from cdk.stacks.infra_stack import InfraStack
from cdk.stacks.quicksight_analysis_stack import QuickSightAnalysisStack
from cdk.stacks.quicksight_chatagent_stack import QuickSightChatAgentStack
from cdk.stacks.quicksight_stack import QuickSightStack
from cdk.stacks.quicksight_topics_stack import QuickSightTopicsStack
from conversational_analytics.env import load_env


def load_environment() -> dict[str, str]:
    """Load environment variables from .env files.

    Looks for .env files in this order:
    1. .env (general)
    2. .env.local (local overrides)
    3. .env.<username> (user-specific, e.g., .env.dev)

    Returns:
        Dictionary with required environment variables
    """
    load_env(project_root)
    username = getpass.getuser()

    # Validate required environment variables
    required_vars = ["AWS_ACCOUNT_ID", "AWS_REGION"]
    optional_vars = {
        "QUICKSIGHT_USER_ARN": None,
        "QUICKSIGHT_NAMESPACE": "default",
        "S3_BUCKET_PREFIX": "conversational-analytics",
        "QUICKSIGHT_ADDITIONAL_USERS": None,
    }

    env_config = {}

    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            print(f"ERROR: Required environment variable {var} is not set.")
            print(f"Please create a .env file or .env.{username} file with your AWS configuration.")
            print("See .env.example for the template.")
            sys.exit(1)
        env_config[var] = value

    for var, default in optional_vars.items():
        env_config[var] = os.environ.get(var, default)

    return env_config


def main():
    """Create CDK app and instantiate Conversational Analytics stacks."""
    # Load environment configuration
    env_config = load_environment()

    # Create CDK app
    app = cdk.App()

    # Define the AWS environment
    aws_env = cdk.Environment(
        account=env_config["AWS_ACCOUNT_ID"],
        region=env_config["AWS_REGION"],
    )

    # ==========================================================================
    # Stack 1: Infrastructure (Stateful - rarely changes)
    # ==========================================================================
    # S3 buckets, Glue database, Athena workgroup
    # Enable QuickSight bucket policies since we'll deploy QuickSight stack
    infra_stack = InfraStack(
        app,
        "ConversationalAnalytics-Infra",
        env=aws_env,
        s3_bucket_prefix=env_config["S3_BUCKET_PREFIX"],
        enable_quicksight_bucket_policy=True,  # Grant QuickSight S3 access
        description="Infrastructure - S3, Glue DB, Athena workgroup (synthetic demo data; real personal or card data requires GDPR/PCI DSS compliance)",
    )

    # ==========================================================================
    # Stack 2: Glue Tables (Stateless - can iterate freely)
    # ==========================================================================
    # Table definitions that reference the data lake bucket
    # Depends on InfraStack for bucket name
    glue_tables_stack = GlueTablesStack(
        app,
        "ConversationalAnalytics-GlueTables",
        env=aws_env,
        data_lake_bucket_name=infra_stack.data_lake_bucket.bucket_name,
        description="Glue Tables - Table definitions for all 6 domain tables (synthetic demo data; real personal or card data requires GDPR/PCI DSS compliance)",
    )
    glue_tables_stack.add_stack_dependency(infra_stack)

    # ==========================================================================
    # Stack 3: QuickSight DataSets (Separate deployment)
    # ==========================================================================
    # DataSource, DataSets (raw + joined), Group, GroupMembership
    # Only created if QUICKSIGHT_USER_ARN is configured
    if env_config.get("QUICKSIGHT_USER_ARN"):
        additional_users_raw = env_config.get("QUICKSIGHT_ADDITIONAL_USERS")
        additional_member_usernames = (
            [u.strip() for u in additional_users_raw.split(",") if u.strip()]
            if additional_users_raw
            else []
        )

        quicksight_stack = QuickSightStack(
            app,
            "ConversationalAnalytics-QuickSight",
            env=aws_env,
            quicksight_user_arn=env_config["QUICKSIGHT_USER_ARN"],
            quicksight_namespace=env_config.get("QUICKSIGHT_NAMESPACE", "default"),
            athena_workgroup_name="conversational-analytics-workgroup",
            data_lake_bucket_name=infra_stack.data_lake_bucket.bucket_name,
            additional_member_usernames=additional_member_usernames,
            description="QuickSight - DataSource and DataSets (synthetic demo data; real personal or card data requires GDPR/PCI DSS compliance)",
        )
        # QuickSight depends on both Infra (Athena workgroup) and GlueTables (table definitions)
        quicksight_stack.add_stack_dependency(infra_stack)
        quicksight_stack.add_stack_dependency(glue_tables_stack)

        # ==========================================================================
        # Stack 4: QuickSight Topics (Separate from DataSets for safe iteration)
        # ==========================================================================
        # Q Topics for natural language queries
        # Separated from DataSets stack so Topic refresh failures don't roll back datasets
        topics_stack = QuickSightTopicsStack(
            app,
            "ConversationalAnalytics-QuickSight-Topics",
            env=aws_env,
            quicksight_user_arn=env_config["QUICKSIGHT_USER_ARN"],
            quicksight_namespace=env_config.get("QUICKSIGHT_NAMESPACE", "default"),
            description="QuickSight Topics - Q Topics for natural language queries (synthetic demo data; real personal or card data requires GDPR/PCI DSS compliance)",
        )
        topics_stack.add_stack_dependency(quicksight_stack)

        # ==========================================================================
        # Stack 5: QuickSight Analysis (Optional - for dashboards and visualizations)
        # ==========================================================================
        # Creates Analysis shells with dataset references
        # After deployment, build visualizations in QuickSight Console
        # Then export with scripts/export_analysis_definition.py for version control
        # Use exported definition if available (from scripts/export_analysis_definition.py)
        analysis_definition_file = str(project_root / "quicksight" / "analyses" / "conversational-analytics-cards-health-monitor.json")
        analysis_stack = QuickSightAnalysisStack(
            app,
            "ConversationalAnalytics-QuickSight-Analysis",
            env=aws_env,
            quicksight_user_arn=env_config["QUICKSIGHT_USER_ARN"],
            definition_file=analysis_definition_file,
            description="QuickSight Analysis - Dashboards showcasing ML anomaly detection (synthetic demo data; real personal or card data requires GDPR/PCI DSS compliance)",
        )
        analysis_stack.add_stack_dependency(quicksight_stack)

        # ==========================================================================
        # Stack 6: QuickSight Chat Agent (Optional - Amazon Quick custom agent)
        # ==========================================================================
        # Custom chat agent (native CfnAgent; permissions via AwsCustomResource).
        # Depends on the QuickSight stack for the group ARN.
        chat_agent_stack = QuickSightChatAgentStack(
            app,
            "ConversationalAnalytics-QuickSight-ChatAgent",
            env=aws_env,
            quicksight_user_arn=env_config["QUICKSIGHT_USER_ARN"],
            quicksight_namespace=env_config.get("QUICKSIGHT_NAMESPACE", "default"),
            description="QuickSight Chat Agent - Amazon Quick custom chat agent (synthetic demo data; real personal or card data requires GDPR/PCI DSS compliance)",
        )
        chat_agent_stack.add_stack_dependency(quicksight_stack)
    else:
        print("INFO: QUICKSIGHT_USER_ARN not set. QuickSight stacks will not be created.")
        print("      Set QUICKSIGHT_USER_ARN in your .env file to enable QuickSight deployment.")

    # cdk-nag AWS Solutions checks run on every synth; findings print as errors/warnings.
    # Accepted findings are suppressed next to the resource, with a reason.
    cdk.Aspects.of(app).add(AwsSolutionsChecks(reports=True, verbose=True))

    # Synthesize the app
    app.synth()


if __name__ == "__main__":
    main()
