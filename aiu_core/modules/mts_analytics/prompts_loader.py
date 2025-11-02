"""Utilities for loading default prompts."""
from __future__ import annotations

import os
from typing import Dict

import yaml

PROMPTS_PATH = os.path.join(os.path.dirname(__file__), "prompts.yaml")


def load_default_prompts() -> Dict[str, str]:
    """Load prompts bundled with the module."""
    if not os.path.exists(PROMPTS_PATH):
        return {}
    with open(PROMPTS_PATH, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data

