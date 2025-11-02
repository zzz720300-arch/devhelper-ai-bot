"""Adapter for Habr Freelance."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def send_response(order_id: str, message: str) -> None:
    logger.info("Sending response to Habr order %s: %s", order_id, message)
