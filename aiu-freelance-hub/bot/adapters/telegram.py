"""Adapter for sending responses via Telegram chats."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def send_response(chat_id: str, message: str) -> None:
    logger.info("Sending Telegram message to %s: %s", chat_id, message)
