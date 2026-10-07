# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CDK stack definitions for Conversational Analytics infrastructure.

Stack Architecture:
- InfraStack: S3 buckets, Glue database, Athena workgroup (stateful)
- GlueTablesStack: Glue table definitions (stateless, can iterate freely)
- QuickSightStack: DataSource, DataSets, Q Topics (separate deployment)

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from .glue_tables_stack import GlueTablesStack
from .infra_stack import InfraStack
from .quicksight_stack import QuickSightStack

__all__ = [
    "GlueTablesStack",
    "InfraStack",
    "QuickSightStack",
]
