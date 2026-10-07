# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Render docs/images/architecture.html to architecture.png (3200x1344).

Usage: uv run --with playwright python docs/images/render_architecture.py
(first run: uv run --with playwright playwright install chromium)
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2000, "height": 840}, device_scale_factor=1.6)
    page.goto((HERE / "architecture.html").as_uri())
    page.screenshot(path=str(HERE / "architecture.png"))
    browser.close()
