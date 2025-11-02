"""Client for interacting with the configured LLM endpoint."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable

import requests

LLM_INTERNAL_URL = os.getenv("LLM_INTERNAL_URL", "")
LLM_INTERNAL_TOKEN = os.getenv("LLM_INTERNAL_TOKEN", "")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "20"))


def call_llm(
    prompt: str,
    *,
    history: Iterable[Dict[str, Any]] | None = None,
    mode: str = "qa",
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Call the configured LLM and return its response.

    If the model endpoint is unreachable, a fallback response is returned with
    ``status == "degraded"`` to let the caller know that the platform is
    running in a degraded mode.
    """

    payload = {
        "prompt": prompt,
        "max_tokens": 900,
        "temperature": 0.35,
        "mode": mode,
    }
    if meta:
        payload["meta"] = meta
    if history:
        payload["history"] = list(history)

    if LLM_INTERNAL_URL:
        try:
            headers = {"Content-Type": "application/json"}
            if LLM_INTERNAL_TOKEN:
                headers["Authorization"] = f"Bearer {LLM_INTERNAL_TOKEN}"
            response = requests.post(
                LLM_INTERNAL_URL,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=LLM_TIMEOUT,
            )
            if response.status_code == 200:
                data = response.json()
                text = data.get("text") or data.get("answer") or ""
                return {
                    "status": "ok",
                    "text": text,
                    "raw": data,
                    "raw_reasoning": data.get("reasoning", ""),
                }
        except Exception:  # pragma: no cover - network failure is external
            pass

    # Fallback response when the model cannot be reached.
    return {
        "status": "degraded",
        "text": (
            "[demo] LLM сейчас недоступна. Но модуль MTS Analytics работает. "
            "Введите ваш запрос ещё раз после подключения модели."
        ),
        "raw": {},
        "raw_reasoning": "llm not available",
    }

