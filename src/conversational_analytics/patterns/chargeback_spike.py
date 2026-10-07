# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
UC-2 Chargeback Root Cause Analysis Pattern Configuration.

Business Question: "Why did chargebacks increase in the week of January 15th, 2026?"

Expected Discovery Path:
1. Spike detection: 3.5x increase during week of 2026-01-15
2. Root cause: Merchant "FastShop Online" (ECOM channel)
3. Type breakdown: 85% unauthorized chargebacks
4. Reason code: 65% "fraud_card_not_present"

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

from conversational_analytics.schema_definitions import ChargebackReasonCode, MerchantChannel

# =============================================================================
# SPIKE TIMING
# =============================================================================

SPIKE_START_DATE = date(2026, 1, 15)
SPIKE_END_DATE = date(2026, 1, 21)
SPIKE_WEEK_DATES = [
    date(2026, 1, 15),
    date(2026, 1, 16),
    date(2026, 1, 17),
    date(2026, 1, 18),
    date(2026, 1, 19),
    date(2026, 1, 20),
    date(2026, 1, 21),
]

# Data generation window (for context around the spike)
DATA_START_DATE = date(2025, 7, 1)  # 6 months before spike
DATA_END_DATE = date(2026, 2, 28)  # 1+ month after spike


# =============================================================================
# FASTSHOP MERCHANT CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class FraudMerchant:
    """Merchant associated with the chargeback spike."""
    merchant_id: str
    merchant_name: str
    merchant_category_code: str
    merchant_category_name: str
    channel: str
    country: str
    city: str | None


FASTSHOP_MERCHANT = FraudMerchant(
    merchant_id="M_FASTSHOP_001",
    merchant_name="FastShop Online",
    merchant_category_code="5964",  # Direct Marketing / E-commerce
    merchant_category_name="Direct Marketing",
    channel=MerchantChannel.ECOM.value,
    country="ES",  # Based in Spain
    city=None,  # E-commerce - no physical location
)


# =============================================================================
# SPIKE MULTIPLIERS AND DISTRIBUTIONS
# =============================================================================

# Spike intensity
SPIKE_MULTIPLIER = 3.5  # 3.5x increase in chargebacks during spike week

# Baseline daily chargeback rate (pre-spike)
# With 25K total chargebacks over ~8 months (245 days), baseline is ~90-100/day
# We want spike to be dramatic but not unrealistic
BASELINE_DAILY_CHARGEBACKS = 90

# FastShop dominance during spike
FASTSHOP_SPIKE_SHARE = 0.80  # 80% of spike chargebacks are FastShop


# =============================================================================
# CHARGEBACK TYPE DISTRIBUTIONS
# =============================================================================

class TypeDistribution(NamedTuple):
    """Distribution of chargeback types."""
    unauthorized: float
    authorized: float


# Normal period: 30% unauthorized, 70% authorized
BASELINE_TYPE_DISTRIBUTION = TypeDistribution(
    unauthorized=0.30,
    authorized=0.70,
)

# Spike period: 85% unauthorized (fraud attack), 15% authorized
SPIKE_TYPE_DISTRIBUTION = TypeDistribution(
    unauthorized=0.85,
    authorized=0.15,
)


# =============================================================================
# REASON CODE DISTRIBUTIONS
# =============================================================================

# Unauthorized reason codes during baseline (distributed across fraud types)
BASELINE_UNAUTHORIZED_REASONS: dict[ChargebackReasonCode, float] = {
    ChargebackReasonCode.FRAUD_CARD_NOT_PRESENT: 0.40,
    ChargebackReasonCode.FRAUD_COUNTERFEIT: 0.35,
    ChargebackReasonCode.FRAUD_LOST_STOLEN: 0.25,
}

# Unauthorized reason codes during spike (concentrated on CNP fraud)
SPIKE_UNAUTHORIZED_REASONS: dict[ChargebackReasonCode, float] = {
    ChargebackReasonCode.FRAUD_CARD_NOT_PRESENT: 0.65,  # Dominant - e-commerce attack
    ChargebackReasonCode.FRAUD_COUNTERFEIT: 0.20,
    ChargebackReasonCode.FRAUD_LOST_STOLEN: 0.15,
}

# Authorized (dispute) reason codes - same for baseline and spike
AUTHORIZED_REASONS: dict[ChargebackReasonCode, float] = {
    ChargebackReasonCode.MERCHANDISE_NOT_RECEIVED: 0.30,
    ChargebackReasonCode.MERCHANDISE_DEFECTIVE: 0.20,
    ChargebackReasonCode.DUPLICATE_CHARGE: 0.15,
    ChargebackReasonCode.INCORRECT_AMOUNT: 0.15,
    ChargebackReasonCode.SUBSCRIPTION_CANCELLED: 0.10,
    ChargebackReasonCode.OTHER: 0.10,
}


# =============================================================================
# AMOUNT DISTRIBUTIONS (in cents)
# =============================================================================

# Baseline chargeback amounts (normal disputes/fraud)
BASELINE_AMOUNT_MEAN_CENTS = 8500  # $85 average
BASELINE_AMOUNT_STD_CENTS = 4000

# FastShop spike amounts (typically smaller, high-volume fraud)
SPIKE_AMOUNT_MEAN_CENTS = 4500  # $45 average - smaller amounts to avoid detection
SPIKE_AMOUNT_STD_CENTS = 2000
SPIKE_AMOUNT_MIN_CENTS = 1000  # $10 minimum
SPIKE_AMOUNT_MAX_CENTS = 15000  # $150 max - keeps under fraud thresholds


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_spike_date(d: date) -> bool:
    """Check if a date falls within the spike period."""
    return SPIKE_START_DATE <= d <= SPIKE_END_DATE


def get_type_distribution(d: date) -> TypeDistribution:
    """Get chargeback type distribution for a given date."""
    return SPIKE_TYPE_DISTRIBUTION if is_spike_date(d) else BASELINE_TYPE_DISTRIBUTION


def get_unauthorized_reasons(d: date) -> dict[ChargebackReasonCode, float]:
    """Get unauthorized reason code distribution for a given date."""
    return SPIKE_UNAUTHORIZED_REASONS if is_spike_date(d) else BASELINE_UNAUTHORIZED_REASONS


def get_daily_chargeback_target(d: date) -> int:
    """Get target number of chargebacks for a given date."""
    base = BASELINE_DAILY_CHARGEBACKS
    if is_spike_date(d):
        return int(base * SPIKE_MULTIPLIER)
    return base


def calculate_spike_chargebacks() -> dict[str, int]:
    """Calculate expected chargeback counts for validation."""
    spike_days = len(SPIKE_WEEK_DATES)
    spike_daily = int(BASELINE_DAILY_CHARGEBACKS * SPIKE_MULTIPLIER)

    total_spike = spike_days * spike_daily
    fastshop_spike = int(total_spike * FASTSHOP_SPIKE_SHARE)
    unauthorized_spike = int(total_spike * SPIKE_TYPE_DISTRIBUTION.unauthorized)
    cnp_fraud_spike = int(unauthorized_spike * SPIKE_UNAUTHORIZED_REASONS[ChargebackReasonCode.FRAUD_CARD_NOT_PRESENT])

    return {
        "spike_days": spike_days,
        "spike_daily_target": spike_daily,
        "total_spike_chargebacks": total_spike,
        "fastshop_chargebacks": fastshop_spike,
        "unauthorized_chargebacks": unauthorized_spike,
        "cnp_fraud_chargebacks": cnp_fraud_spike,
    }


# =============================================================================
# PATTERN SUMMARY (for documentation/validation)
# =============================================================================

PATTERN_SUMMARY = {
    "use_case": "UC-2",
    "business_question": "Why did chargebacks increase in the week of January 15th, 2026?",
    "spike_period": f"{SPIKE_START_DATE} to {SPIKE_END_DATE}",
    "spike_multiplier": f"{SPIKE_MULTIPLIER}x",
    "root_cause_merchant": FASTSHOP_MERCHANT.merchant_name,
    "root_cause_channel": FASTSHOP_MERCHANT.channel,
    "merchant_share_during_spike": f"{FASTSHOP_SPIKE_SHARE:.0%}",
    "unauthorized_rate_spike": f"{SPIKE_TYPE_DISTRIBUTION.unauthorized:.0%}",
    "unauthorized_rate_baseline": f"{BASELINE_TYPE_DISTRIBUTION.unauthorized:.0%}",
    "cnp_fraud_rate_spike": f"{SPIKE_UNAUTHORIZED_REASONS[ChargebackReasonCode.FRAUD_CARD_NOT_PRESENT]:.0%}",
    "expected_discovery_path": [
        "1. Detect 3.5x spike in chargebacks week of 2026-01-15",
        "2. Identify FastShop Online as dominant merchant (>80%)",
        "3. Note 85% unauthorized vs 30% baseline",
        "4. See 65% fraud_card_not_present reason code",
    ],
}


if __name__ == "__main__":
    # Print pattern summary for validation
    print("UC-2 Chargeback Spike Pattern Configuration")
    print("=" * 50)
    for key, value in PATTERN_SUMMARY.items():
        if isinstance(value, list):
            print(f"\n{key}:")
            for item in value:
                print(f"  {item}")
        else:
            print(f"{key}: {value}")

    print("\n" + "=" * 50)
    print("Expected Counts During Spike:")
    for key, count in calculate_spike_chargebacks().items():
        print(f"  {key}: {count}")
