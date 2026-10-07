# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Glue Tables Stack - Table definitions for the data lake.

This stack creates Glue tables that reference the data lake S3 bucket.
It depends on the InfraStack and should be deployed after data is uploaded.

Separating tables from infrastructure allows:
1. Faster iteration when adding/modifying table schemas
2. Independent deployment without affecting S3/Athena resources
3. Easier table recreation without data loss

Deployment:
    uv run cdk deploy ConversationalAnalytics-GlueTables

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

import sys
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Fn
from aws_cdk import aws_glue as glue
from constructs import Construct

# Add src to path for schema imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from conversational_analytics.schema_definitions import (
    QS_TO_ATHENA_TYPE,
    QUICKSIGHT_TABLES,
    TABLE_PARTITIONS,
)


class GlueTablesStack(cdk.Stack):
    """Glue tables stack for all 6 domain tables.

    This stack imports the data lake bucket from InfraStack and creates
    Glue table definitions pointing to S3 locations.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        data_lake_bucket_name: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import bucket name from InfraStack or use provided value
        self.data_lake_bucket_name = data_lake_bucket_name or Fn.import_value(
            "ConversationalAnalytics-DataLakeBucket"
        )

        # Create Glue database reference (created by InfraStack)
        self.glue_database_name = "conversational_analytics"

        # Create all tables
        self._create_glue_tables()

        # Outputs
        self._create_outputs()

    def _create_glue_tables(self) -> None:
        """Create Glue tables for all 6 domain tables."""
        self.glue_tables = {}

        for table_name, columns in QUICKSIGHT_TABLES.items():
            partition_keys = TABLE_PARTITIONS.get(table_name, [])
            self.glue_tables[table_name] = self._create_glue_table(
                table_name, columns, partition_keys
            )

    def _create_glue_table(
        self, table_name: str, columns: list, partition_keys: list[str]
    ) -> glue.CfnTable:
        """Create a single Glue table.

        Args:
            table_name: Name of the table
            columns: List of QuickSightColumn definitions
            partition_keys: List of partition column names
        """
        # Build columns (excluding partition columns)
        table_columns = []
        partition_columns = []

        for col in columns:
            athena_type = QS_TO_ATHENA_TYPE.get(col.qs_type, "string")
            column_def = glue.CfnTable.ColumnProperty(
                name=col.name,
                type=athena_type,
                comment=col.description,
            )

            if col.name in partition_keys:
                partition_columns.append(column_def)
            else:
                table_columns.append(column_def)

        # Ensure partition columns are in correct order
        ordered_partition_columns = []
        for pk in partition_keys:
            for pc in partition_columns:
                if pc.name == pk:
                    ordered_partition_columns.append(pc)
                    break

        # S3 location for this table
        s3_location = f"s3://{self.data_lake_bucket_name}/{table_name}/"

        # Create table
        table = glue.CfnTable(
            self,
            f"GlueTable{table_name.title().replace('_', '')}",
            catalog_id=self.account,
            database_name=self.glue_database_name,
            table_input=glue.CfnTable.TableInputProperty(
                name=table_name,
                description=f"{table_name} table",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "classification": "parquet",
                    "compressionType": "snappy",
                    "typeOfData": "file",
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=table_columns,
                    location=s3_location,
                    input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                        parameters={
                            "serialization.format": "1",
                        },
                    ),
                    compressed=True,
                ),
                partition_keys=ordered_partition_columns if partition_keys else None,
            ),
        )

        return table

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        # Output table count for verification
        cdk.CfnOutput(
            self,
            "TableCount",
            value=str(len(self.glue_tables)),
            description="Number of Glue tables created",
        )

        # Output table names
        cdk.CfnOutput(
            self,
            "TableNames",
            value=",".join(self.glue_tables.keys()),
            description="Comma-separated list of table names",
        )
