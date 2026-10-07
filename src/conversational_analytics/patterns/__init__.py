# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Embedded pattern configurations for Conversational Analytics demo scenarios.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from conversational_analytics.patterns.chargeback_spike import (
    AUTHORIZED_REASONS,
    BASELINE_AMOUNT_MEAN_CENTS,
    BASELINE_AMOUNT_STD_CENTS,
    BASELINE_DAILY_CHARGEBACKS,
    BASELINE_TYPE_DISTRIBUTION,
    BASELINE_UNAUTHORIZED_REASONS,
    DATA_END_DATE,
    DATA_START_DATE,
    FASTSHOP_MERCHANT,
    FASTSHOP_SPIKE_SHARE,
    PATTERN_SUMMARY,
    SPIKE_AMOUNT_MAX_CENTS,
    SPIKE_AMOUNT_MEAN_CENTS,
    SPIKE_AMOUNT_MIN_CENTS,
    SPIKE_AMOUNT_STD_CENTS,
    SPIKE_END_DATE,
    SPIKE_MULTIPLIER,
    SPIKE_START_DATE,
    SPIKE_TYPE_DISTRIBUTION,
    SPIKE_UNAUTHORIZED_REASONS,
    SPIKE_WEEK_DATES,
    FraudMerchant,
    TypeDistribution,
    calculate_spike_chargebacks,
    get_daily_chargeback_target,
    get_type_distribution,
    get_unauthorized_reasons,
    is_spike_date,
)

__all__ = [
    # Spike timing
    "SPIKE_START_DATE",
    "SPIKE_END_DATE",
    "SPIKE_WEEK_DATES",
    "DATA_START_DATE",
    "DATA_END_DATE",
    # Merchant
    "FASTSHOP_MERCHANT",
    "FraudMerchant",
    # Multipliers
    "SPIKE_MULTIPLIER",
    "BASELINE_DAILY_CHARGEBACKS",
    "FASTSHOP_SPIKE_SHARE",
    # Type distributions
    "TypeDistribution",
    "BASELINE_TYPE_DISTRIBUTION",
    "SPIKE_TYPE_DISTRIBUTION",
    # Reason code distributions
    "BASELINE_UNAUTHORIZED_REASONS",
    "SPIKE_UNAUTHORIZED_REASONS",
    "AUTHORIZED_REASONS",
    # Amount distributions
    "BASELINE_AMOUNT_MEAN_CENTS",
    "BASELINE_AMOUNT_STD_CENTS",
    "SPIKE_AMOUNT_MEAN_CENTS",
    "SPIKE_AMOUNT_STD_CENTS",
    "SPIKE_AMOUNT_MIN_CENTS",
    "SPIKE_AMOUNT_MAX_CENTS",
    # Helper functions
    "is_spike_date",
    "get_type_distribution",
    "get_unauthorized_reasons",
    "get_daily_chargeback_target",
    "calculate_spike_chargebacks",
    # Summary
    "PATTERN_SUMMARY",
]
