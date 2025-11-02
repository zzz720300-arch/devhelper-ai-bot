"""Configuration helpers for the MTS Analytics module."""
from __future__ import annotations

import logging
import os
from pathlib import Path

MTS_MAX_HISTORY = int(os.getenv("MTS_MAX_HISTORY", "10"))
MTS_DEFAULT_MODE = os.getenv("MTS_DEFAULT_MODE", "qa")
MTS_ADMIN_TOKEN = os.getenv("MTS_ADMIN_TOKEN", "")

LOG_FILE = os.getenv("MTS_LOG_FILE", "/srv/logs/aiu-core/mts_analytics.log")
log_path = Path(LOG_FILE)
log_path.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("mts_analytics")
if not logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

MTS_LOGGER = logger

