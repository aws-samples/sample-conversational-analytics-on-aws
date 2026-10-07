# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Synthetic data generators for Conversational Analytics tables.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from .base import (
    RANDOM_SEED,
    distribute_counts,
    generate_id,
    generate_ids,
    get_data_dir,
    now_utc,
    set_seed,
    weighted_choice,
    write_parquet,
)
from .cards import generate_cards, save_cards
from .chargebacks import generate_chargebacks, save_chargebacks
from .customers import generate_customers, save_customers
from .merchants import generate_merchants, save_merchants
from .tokenizations import generate_tokenizations, save_tokenizations
from .transactions import generate_transactions, save_transactions

__all__ = [
    # Base utilities
    "RANDOM_SEED",
    "distribute_counts",
    "generate_id",
    "generate_ids",
    "get_data_dir",
    "now_utc",
    "set_seed",
    "weighted_choice",
    "write_parquet",
    # Generators
    "generate_merchants",
    "save_merchants",
    "generate_customers",
    "save_customers",
    "generate_cards",
    "save_cards",
    "generate_transactions",
    "save_transactions",
    "generate_tokenizations",
    "save_tokenizations",
    "generate_chargebacks",
    "save_chargebacks",
]
