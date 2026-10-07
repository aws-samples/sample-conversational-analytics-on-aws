# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Base generator utilities for synthetic data generation.

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Fixed seed for reproducibility
RANDOM_SEED = 42

# Data output directory (conversational_analytics/data)
# Path: src/conversational_analytics/generators/base.py -> parent x4 = conversational_analytics/
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


def set_seed(seed: int = RANDOM_SEED) -> np.random.Generator:
    """Set random seed and return a generator."""
    return np.random.default_rng(seed)


def get_data_dir() -> Path:
    """Get the data output directory, creating if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def write_parquet(
    df: pd.DataFrame,
    table_name: str,
    partition_cols: list[str] | None = None,
) -> Path:
    """Write DataFrame to Parquet with snappy compression.

    Args:
        df: DataFrame to write
        table_name: Name of the table (used as directory name)
        partition_cols: Optional list of columns to partition by

    Returns:
        Path to the output directory
    """
    output_dir = get_data_dir() / table_name

    # Clean existing data
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, preserve_index=False)

    if partition_cols:
        pq.write_to_dataset(
            table,
            root_path=str(output_dir),
            partition_cols=partition_cols,
            compression="snappy",
            existing_data_behavior="delete_matching",
        )
    else:
        pq.write_table(
            table,
            output_dir / "data.parquet",
            compression="snappy",
        )

    return output_dir


def generate_id(prefix: str, num: int, width: int = 6) -> str:
    """Generate a padded ID string."""
    return f"{prefix}{num:0{width}d}"


def generate_ids(prefix: str, count: int, width: int = 6, start: int = 1) -> list[str]:
    """Generate a list of padded ID strings."""
    return [generate_id(prefix, i, width) for i in range(start, start + count)]


def now_utc() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


def weighted_choice(
    rng: np.random.Generator,
    options: list,
    weights: list[float],
    size: int | None = None,
) -> np.ndarray:
    """Make weighted random choices."""
    probs = np.array(weights) / sum(weights)
    return rng.choice(options, size=size, p=probs)


def distribute_counts(total: int, weights: dict) -> dict:
    """Distribute a total count according to weights."""
    total_weight = sum(weights.values())
    result = {}
    remaining = total

    items = list(weights.items())
    for i, (key, weight) in enumerate(items):
        if i == len(items) - 1:
            result[key] = remaining
        else:
            count = int(total * weight / total_weight)
            result[key] = count
            remaining -= count

    return result
