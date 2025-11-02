"""Database models and helpers for the MTS Analytics module."""
from __future__ import annotations

import os
from typing import Dict, Iterable

import psycopg2

PG_DSN = os.getenv(
    "MTS_PG_DSN",
    os.getenv("CODEX_PG_DSN", "dbname=aiu_core user=aiu_core password=aiu_core host=127.0.0.1"),
)


def _conn():  # pragma: no cover - thin wrapper
    return psycopg2.connect(PG_DSN)


def init_tables() -> None:
    """Create the required tables if they do not exist."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS mts_analytics_logs (
        id SERIAL PRIMARY KEY,
        trace_id UUID,
        session_id VARCHAR(128),
        user_query TEXT,
        answer TEXT,
        used_tools TEXT,
        duration_ms INT,
        created_at TIMESTAMP DEFAULT NOW()
    );
        """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS mts_analytics_prompts (
        id SERIAL PRIMARY KEY,
        name VARCHAR(128) UNIQUE NOT NULL,
        text TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    );
        """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS mts_analytics_memory (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(128) NOT NULL,
        role VARCHAR(16) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );
        """
    )
    conn.commit()
    conn.close()


def log_interaction(
    *,
    trace_id: str,
    session_id: str,
    user_query: str,
    answer: str,
    used_tools: str,
    duration_ms: int,
) -> None:
    """Insert a record into ``mts_analytics_logs``."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO mts_analytics_logs
        (trace_id, session_id, user_query, answer, used_tools, duration_ms)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (trace_id, session_id, user_query, answer, used_tools, duration_ms),
    )
    conn.commit()
    conn.close()


def get_prompts_from_db() -> Dict[str, str]:
    """Fetch prompts stored in the database."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT name, text FROM mts_analytics_prompts;")
    rows = cur.fetchall()
    conn.close()
    return {name: text for name, text in rows}


def save_prompts_to_db(items: Iterable[Dict[str, str]]) -> None:
    """Upsert prompt definitions into the database."""
    conn = _conn()
    cur = conn.cursor()
    for item in items:
        name = item.get("name")
        text = item.get("text") or ""
        if not name:
            continue
        cur.execute(
            """
            INSERT INTO mts_analytics_prompts (name, text, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (name) DO UPDATE
            SET text = EXCLUDED.text, updated_at = NOW();
            """,
            (name, text),
        )
    conn.commit()
    conn.close()

