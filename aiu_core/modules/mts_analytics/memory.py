"""Dialogue memory backends for the MTS Analytics agent."""
from __future__ import annotations

import json
import os
import time
from typing import Dict, List

import psycopg2
import redis

BACKEND = os.getenv("MTS_MEMORY_BACKEND", os.getenv("CODEX_MEMORY_BACKEND", "redis"))
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
PG_DSN = os.getenv(
    "MTS_PG_DSN",
    os.getenv("CODEX_PG_DSN", "dbname=aiu_core user=aiu_core password=aiu_core host=127.0.0.1"),
)


def get_history(session_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """Return conversation history for the provided ``session_id``."""
    if BACKEND == "postgres":
        return _pg_get_history(session_id, limit)
    return _redis_get_history(session_id, limit)


def save_message(session_id: str, role: str, content: str) -> None:
    """Persist a single message to the configured backend."""
    if BACKEND == "postgres":
        _pg_save_message(session_id, role, content)
    else:
        _redis_save_message(session_id, role, content)


# ------------------------------ Redis backend ------------------------------


def _redis_client() -> "redis.Redis":
    return redis.from_url(REDIS_URL)


def _redis_get_history(session_id: str, limit: int) -> List[Dict[str, str]]:
    client = _redis_client()
    key = f"mts_analytics:{session_id}"
    raw_items = client.lrange(key, -limit, -1)
    history: List[Dict[str, str]] = []
    for raw in raw_items:
        try:
            history.append(json.loads(raw))
        except Exception:  # pragma: no cover - malformed entry should be ignored
            continue
    return history


def _redis_save_message(session_id: str, role: str, content: str) -> None:
    client = _redis_client()
    key = f"mts_analytics:{session_id}"
    client.rpush(
        key,
        json.dumps({"role": role, "content": content, "ts": time.time()}, ensure_ascii=False),
    )
    client.expire(key, 60 * 60 * 6)  # six hours


# ---------------------------- PostgreSQL backend ---------------------------


def _pg_conn():  # pragma: no cover - simple wrapper
    return psycopg2.connect(PG_DSN)


def _pg_get_history(session_id: str, limit: int) -> List[Dict[str, str]]:
    conn = _pg_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content
        FROM mts_analytics_memory
        WHERE session_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (session_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    history: List[Dict[str, str]] = []
    for role, content in reversed(rows):
        history.append({"role": role, "content": content})
    return history


def _pg_save_message(session_id: str, role: str, content: str) -> None:
    conn = _pg_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO mts_analytics_memory (session_id, role, content)
        VALUES (%s, %s, %s);
        """,
        (session_id, role, content),
    )
    conn.commit()
    conn.close()

