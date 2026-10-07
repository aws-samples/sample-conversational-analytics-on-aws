#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Export QuickSight Analysis definition for version control.

After building visualizations in QuickSight Console, run this script
to export the definition. The exported JSON can then be used by CDK
for reproducible deployments.

Usage:
    uv run python scripts/export_analysis_definition.py [analysis-id]

Example:
    uv run python scripts/export_analysis_definition.py conversational-analytics-cards-health-monitor

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import boto3

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conversational_analytics.env import load_env

# Same .env precedence as the CDK app (see conversational_analytics.env)
load_env()



def _json_default(value):
    """Serialize boto3 datetimes as ISO 8601 (with 'T'), which CloudFormation requires."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)

def export_analysis(analysis_id: str, output_dir: str = "quicksight/analyses") -> str:
    """Export an analysis definition to JSON.

    Args:
        analysis_id: The QuickSight analysis ID
        output_dir: Directory to save the exported definition

    Returns:
        Path to the exported file
    """
    region = os.getenv("AWS_REGION", "eu-west-1")
    account_id = os.getenv("AWS_ACCOUNT_ID")

    if not account_id:
        # Try to get from STS
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

    client = boto3.client("quicksight", region_name=region)

    print(f"Exporting analysis: {analysis_id}")
    print(f"Account: {account_id}, Region: {region}")

    # Get the analysis definition
    try:
        response = client.describe_analysis_definition(
            AwsAccountId=account_id,
            AnalysisId=analysis_id,
        )
    except client.exceptions.ResourceNotFoundException:
        print(f"Error: Analysis '{analysis_id}' not found")
        sys.exit(1)

    # Mask the account ID so exports are safe to commit; the analysis stack
    # rewrites dataset ARNs for the target account at deploy time
    for ds_decl in response.get("Definition", {}).get("DataSetIdentifierDeclarations", []):
        ds_decl["DataSetArn"] = ds_decl["DataSetArn"].replace(account_id, "123456789012")

    # Extract the relevant parts
    definition = {
        "ComplianceNote": (
            "All data shown by this analysis is synthetic. Real EU personal data or payment card data "
            "would fall under GDPR and PCI DSS, which are the deployer's responsibility."
        ),
        "Name": response.get("Name"),
        "AnalysisId": response.get("AnalysisId"),
        "Definition": response.get("Definition"),
        "ThemeArn": response.get("ThemeArn"),
        "ExportedAt": datetime.utcnow().isoformat(),
        "ExportedFrom": {
            "Region": region,
        },
    }

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write to file
    filename = f"{analysis_id}.json"
    filepath = output_path / filename

    with open(filepath, "w") as f:
        json.dump(definition, f, indent=2, default=_json_default)

    print(f"\nExported to: {filepath}")

    # Print summary
    if "Definition" in definition and definition["Definition"]:
        sheets = definition["Definition"].get("Sheets", [])
        print(f"Sheets: {len(sheets)}")
        for sheet in sheets:
            sheet_id = sheet.get("SheetId", "unknown")
            sheet_name = sheet.get("Name", "Unnamed")
            visuals = sheet.get("Visuals", [])
            print(f"  - {sheet_name} ({sheet_id}): {len(visuals)} visuals")

    return str(filepath)


def list_analyses() -> None:
    """List all analyses in the account."""
    region = os.getenv("AWS_REGION", "eu-west-1")
    account_id = os.getenv("AWS_ACCOUNT_ID")

    if not account_id:
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

    client = boto3.client("quicksight", region_name=region)

    print(f"Listing analyses in {account_id} ({region}):\n")

    paginator = client.get_paginator("list_analyses")
    for page in paginator.paginate(AwsAccountId=account_id):
        for analysis in page.get("AnalysisSummaryList", []):
            analysis_id = analysis.get("AnalysisId")
            name = analysis.get("Name")
            status = analysis.get("Status")
            print(f"  {analysis_id}")
            print(f"    Name: {name}")
            print(f"    Status: {status}")
            print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python export_analysis_definition.py <analysis-id>")
        print("       python export_analysis_definition.py --list")
        print()
        print("Examples:")
        print("  python export_analysis_definition.py conversational-analytics-cards-health-monitor")
        print("  python export_analysis_definition.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_analyses()
    else:
        analysis_id = sys.argv[1]
        export_analysis(analysis_id)


if __name__ == "__main__":
    main()
