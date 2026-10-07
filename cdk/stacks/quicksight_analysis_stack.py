# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""QuickSight Analysis Stack - Dashboards and Visualizations.

This stack creates QuickSight Analyses that showcase the embedded patterns
in the Conversational Analytics data through visual dashboards.

The approach:
1. CDK creates the Analysis shell with dataset references
2. Build visualizations in QuickSight Console (much easier than CDK)
3. Export definition via CLI for version control
4. Re-import via CDK for reproducibility

Usage:
    uv run cdk deploy ConversationalAnalytics-QuickSight-Analysis

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import json
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Fn
from aws_cdk import aws_quicksight as quicksight
from constructs import Construct


class QuickSightAnalysisStack(cdk.Stack):
    """QuickSight Analysis stack for Conversational Analytics dashboards.

    Creates:
    - Cards Domain Health Monitor Analysis
    - Can load from exported definition JSON if available

    Prerequisites:
    - ConversationalAnalytics-QuickSight stack deployed (DataSource, DataSets)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        quicksight_user_arn: str,
        quicksight_group_arn: str | None = None,
        definition_file: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.quicksight_user_arn = quicksight_user_arn
        self.quicksight_group_arn = quicksight_group_arn or Fn.import_value(
            "ConversationalAnalytics-QuickSightGroup"
        )

        # Check if we have an exported definition to use
        self.definition_file = definition_file
        if definition_file and Path(definition_file).exists():
            self._create_analysis_from_definition(definition_file)
        else:
            self._create_analysis_shell()

    def _get_dataset_arns(self) -> dict[str, str]:
        """Get ARNs for the joined datasets."""
        datasets = {
            "chargeback-analysis": f"arn:aws:quicksight:{self.region}:{self.account}:dataset/conversational-analytics-chargeback-analysis",
            "spending-analysis": f"arn:aws:quicksight:{self.region}:{self.account}:dataset/conversational-analytics-spending-analysis",
            "tokenization-analysis": f"arn:aws:quicksight:{self.region}:{self.account}:dataset/conversational-analytics-tokenization-analysis",
            "customer-cards": f"arn:aws:quicksight:{self.region}:{self.account}:dataset/conversational-analytics-customer-cards",
            "card-delivery": f"arn:aws:quicksight:{self.region}:{self.account}:dataset/conversational-analytics-card-delivery",
        }
        return datasets

    def _get_permissions(self) -> list:
        """Get permissions for the analysis."""
        actions = [
            "quicksight:DescribeAnalysis",
            "quicksight:DescribeAnalysisPermissions",
            "quicksight:QueryAnalysis",
            "quicksight:UpdateAnalysis",
            "quicksight:UpdateAnalysisPermissions",
            "quicksight:DeleteAnalysis",
            "quicksight:RestoreAnalysis",
        ]

        permissions = [
            quicksight.CfnAnalysis.ResourcePermissionProperty(
                principal=self.quicksight_user_arn,
                actions=actions,
            ),
        ]

        # Analyses have no viewer role (sharing makes co-owners), so the group isn't
        # granted access. Share a published dashboard with the group instead.

        return permissions

    def _create_analysis_shell(self) -> None:
        """Create a minimal analysis shell that can be customized in console.

        This creates the analysis with:
        - Dataset references
        - Empty sheet placeholders
        - Permissions

        After deployment, open in QuickSight Console to add visualizations.
        """
        dataset_arns = self._get_dataset_arns()

        # Dataset identifier mappings for the definition
        dataset_identifiers = [
            quicksight.CfnAnalysis.DataSetIdentifierDeclarationProperty(
                identifier="chargeback-analysis",
                data_set_arn=dataset_arns["chargeback-analysis"],
            ),
            quicksight.CfnAnalysis.DataSetIdentifierDeclarationProperty(
                identifier="spending-analysis",
                data_set_arn=dataset_arns["spending-analysis"],
            ),
            quicksight.CfnAnalysis.DataSetIdentifierDeclarationProperty(
                identifier="tokenization-analysis",
                data_set_arn=dataset_arns["tokenization-analysis"],
            ),
            quicksight.CfnAnalysis.DataSetIdentifierDeclarationProperty(
                identifier="customer-cards",
                data_set_arn=dataset_arns["customer-cards"],
            ),
            quicksight.CfnAnalysis.DataSetIdentifierDeclarationProperty(
                identifier="card-delivery",
                data_set_arn=dataset_arns["card-delivery"],
            ),
        ]

        # Create sheet definitions - these are placeholders
        # Add visuals in QuickSight Console, then export
        sheets = [
            quicksight.CfnAnalysis.SheetDefinitionProperty(
                sheet_id="executive-overview",
                name="Executive Overview",
                description="High-level KPIs and trends across the Cards domain",
            ),
            quicksight.CfnAnalysis.SheetDefinitionProperty(
                sheet_id="chargeback-analysis",
                name="Chargeback Analysis",
                description="Chargeback trends with ML anomaly detection - showcases FastShop Online fraud spike",
            ),
            quicksight.CfnAnalysis.SheetDefinitionProperty(
                sheet_id="tokenization-insights",
                name="Tokenization Insights",
                description="Digital wallet adoption timing by country",
            ),
            quicksight.CfnAnalysis.SheetDefinitionProperty(
                sheet_id="customer-segmentation",
                name="Customer Segmentation",
                description="Metal vs Standard tier spending patterns and card ownership",
            ),
            quicksight.CfnAnalysis.SheetDefinitionProperty(
                sheet_id="delivery-performance",
                name="Delivery Performance",
                description="Card delivery times by country and delivery type",
            ),
        ]

        # Analysis definition
        definition = quicksight.CfnAnalysis.AnalysisDefinitionProperty(
            data_set_identifier_declarations=dataset_identifiers,
            sheets=sheets,
            analysis_defaults=quicksight.CfnAnalysis.AnalysisDefaultsProperty(
                default_new_sheet_configuration=quicksight.CfnAnalysis.DefaultNewSheetConfigurationProperty(
                    interactive_layout_configuration=quicksight.CfnAnalysis.DefaultInteractiveLayoutConfigurationProperty(
                        grid=quicksight.CfnAnalysis.DefaultGridLayoutConfigurationProperty(
                            canvas_size_options=quicksight.CfnAnalysis.GridLayoutCanvasSizeOptionsProperty(
                                screen_canvas_size_options=quicksight.CfnAnalysis.GridLayoutScreenCanvasSizeOptionsProperty(
                                    resize_option="FIXED",
                                    optimized_view_port_width="1600px",
                                )
                            )
                        )
                    ),
                    sheet_content_type="INTERACTIVE",
                )
            ),
        )

        # Create the analysis
        self.analysis = quicksight.CfnAnalysis(
            self,
            "CardsHealthMonitor",
            aws_account_id=self.account,
            analysis_id="conversational-analytics-cards-health-monitor",
            name="Cards Domain Health Monitor",
            definition=definition,
            permissions=self._get_permissions(),
            validation_strategy=quicksight.CfnAnalysis.ValidationStrategyProperty(
                mode="LENIENT"  # Allow deployment even with empty sheets
            ),
        )

        # Output the analysis ARN
        cdk.CfnOutput(
            self,
            "AnalysisArn",
            value=self.analysis.attr_arn,
            description="ARN of the Cards Health Monitor Analysis",
            export_name="ConversationalAnalytics-AnalysisArn",
        )

        cdk.CfnOutput(
            self,
            "AnalysisUrl",
            value=f"https://{self.region}.quicksight.aws.amazon.com/sn/analyses/conversational-analytics-cards-health-monitor",
            description="URL to open the analysis in QuickSight Console",
        )

    def _create_analysis_from_definition(self, definition_file: str) -> None:
        """Create analysis from an exported definition JSON file.

        The exported JSON uses PascalCase keys (AWS API format). We bypass CDK's
        JSII type checking via add_property_override to pass the raw definition
        straight to CloudFormation.
        """
        with open(definition_file) as f:
            exported = json.load(f)

        # The exported definition needs dataset ARNs updated for this account/region
        dataset_arns = self._get_dataset_arns()

        definition_dict = exported["Definition"]

        # Update dataset ARNs in the definition for this account/region
        for ds_decl in definition_dict.get("DataSetIdentifierDeclarations", []):
            identifier = ds_decl.get("Identifier", "")
            if identifier in dataset_arns:
                ds_decl["DataSetArn"] = dataset_arns[identifier]

        # Create the analysis shell (definition will be overridden below)
        self.analysis = quicksight.CfnAnalysis(
            self,
            "CardsHealthMonitor",
            aws_account_id=self.account,
            analysis_id="conversational-analytics-cards-health-monitor",
            name=exported.get("Name", "Cards Domain Health Monitor"),
            permissions=self._get_permissions(),
            validation_strategy=quicksight.CfnAnalysis.ValidationStrategyProperty(
                mode="LENIENT"
            ),
        )

        # Override with the full exported definition in PascalCase (CloudFormation format)
        # This bypasses JSII type checking which expects snake_case keys
        self.analysis.add_property_override("Definition", definition_dict)

        cdk.CfnOutput(
            self,
            "AnalysisArn",
            value=self.analysis.attr_arn,
            description="ARN of the Cards Health Monitor Analysis",
            export_name="ConversationalAnalytics-AnalysisArn",
        )

        cdk.CfnOutput(
            self,
            "AnalysisUrl",
            value=f"https://{self.region}.quicksight.aws.amazon.com/sn/analyses/conversational-analytics-cards-health-monitor",
            description="URL to open the analysis in QuickSight Console",
        )
