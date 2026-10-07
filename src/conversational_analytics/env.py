# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Shared .env loading for the CDK app and the scripts.

Both must resolve the same configuration, so they load the same files in the
same order. Later files override earlier ones and any variables already set in
the shell:

1. ``.env`` (general)
2. ``.env.local`` (local overrides)
3. ``.env.<username>`` (user-specific, e.g. ``.env.dev``)
"""

import getpass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env(project_root: Path = PROJECT_ROOT) -> None:
    """Load .env files from ``project_root`` in precedence order."""
    for name in (".env", ".env.local", f".env.{getpass.getuser()}"):
        env_path = project_root / name
        if env_path.exists():
            load_dotenv(env_path, override=True)
