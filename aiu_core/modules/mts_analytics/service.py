"""Business logic for the MTS Analytics agent."""
from __future__ import annotations

import json
import time
import uuid
from typing import Dict, List

from .config import (
    MTS_ADMIN_TOKEN,
    MTS_DEFAULT_MODE,
    MTS_LOGGER,
    MTS_MAX_HISTORY,
)
from .llm_client import call_llm
from .memory import get_history, save_message
from .models import (
    get_prompts_from_db,
    init_tables,
    log_interaction,
    save_prompts_to_db,
)
from .prompts_loader import load_default_prompts

# Initialise database tables when the module is imported. Failures are logged
# but should not block the rest of the application from starting.
try:  # pragma: no cover - defensive guard
    init_tables()
except Exception as exc:  # pragma: no cover - we cannot guarantee DB access
    MTS_LOGGER.warning("tables init failed: %s", exc)


def handle_query(payload: Dict | None) -> Dict:
    """Handle an incoming analytics query."""
    ts = time.time()
    trace_id = str(uuid.uuid4())

    payload = payload or {}
    user_query = payload.get("user_query")
    session_id = payload.get("session_id") or f"anon-{trace_id[:8]}"
    mode = payload.get("mode") or MTS_DEFAULT_MODE
    meta = payload.get("meta") or {}

    if not user_query:
        return {
            "status": "error",
            "error": "user_query is required",
            "trace_id": trace_id,
        }

    # 1. Fetch conversation history from the configured backend.
    history = get_history(session_id, limit=MTS_MAX_HISTORY)

    # 2. Load prompts from DB and defaults.
    db_prompts = get_prompts_from_db()
    default_prompts = load_default_prompts()

    system_prompt = (
        db_prompts.get("system_default")
        or default_prompts.get("system_default")
        or (
            "Ты — LLM-агент MTS Analytics в ядре AIU-CORE. Отвечай по-русски. "
            "Если просят SQL — используй синтаксис PostgreSQL. Если просят промт — "
            "сделай хороший, структурированный промт."
        )
    )

    # 3. Build the final prompt to send to the LLM.
    final_prompt = build_prompt(system_prompt, history, user_query, mode)

    # 4. Call the LLM service.
    llm_result = call_llm(final_prompt, history=history, mode=mode, meta=meta)

    answer_text = (
        llm_result.get("text")
        or "Модель не дала ответа. Проверь подключение LLM."
    )
    duration_ms = int((time.time() - ts) * 1000)

    # 5. Persist the dialogue history.
    save_message(session_id, "user", user_query)
    save_message(session_id, "assistant", answer_text)

    # 6. Persist logs to DB and file.
    log_interaction(
        trace_id=trace_id,
        session_id=session_id,
        user_query=user_query,
        answer=answer_text,
        used_tools="llm,memory,prompts",
        duration_ms=duration_ms,
    )

    MTS_LOGGER.info(
        json.dumps(
            {
                "trace_id": trace_id,
                "session_id": session_id,
                "user_query": user_query,
                "answer": answer_text,
                "mode": mode,
                "duration_ms": duration_ms,
            },
            ensure_ascii=False,
        )
    )

    status = llm_result.get("status") or "ok"

    response = {
        "status": status,
        "answer": answer_text,
        "reasoning": llm_result.get("raw_reasoning", "hidden"),
        "used_tools": ["llm", "memory", "prompts"],
        "trace_id": trace_id,
    }

    if llm_result.get("raw"):
        response["raw"] = llm_result["raw"]

    return response


def build_prompt(system_prompt: str, history: List[Dict], user_query: str, mode: str) -> str:
    """Compose the final prompt string sent to the language model."""
    parts: List[str] = [system_prompt, "", "История диалога:"]
    for message in history:
        role = message.get("role", "user")
        content = message.get("content", "")
        parts.append(f"{role}: {content}")
    parts.append("")
    parts.append("Текущее сообщение пользователя:")
    parts.append(user_query)

    if mode == "analysis":
        parts.append(
            "Отвечай как аналитик МТС: у тебя есть данные по абонентам, регионам, "
            "периодам. Можно предлагать SQL, Python/pandas и этапы анализа."
        )
    elif mode == "nlp":
        parts.append(
            "Отвечай как LLM-инженер: составь хороший промт, добавь роли (system, "
            "user), опиши формат ответа, при необходимости предложи few-shot."
        )
    else:  # qa
        parts.append("Отвечай кратко и по делу, но по-русски.")

    return "\n".join(parts)


def list_prompts() -> List[Dict]:
    """Return merged default and DB prompts as a list of dicts."""
    db_prompts = get_prompts_from_db()
    default_prompts = load_default_prompts()
    merged = {**default_prompts, **db_prompts}
    return [{"name": name, "text": text} for name, text in merged.items()]


def update_prompts(payload: Dict | None) -> tuple[bool, str]:
    """Persist prompt updates if the caller is authorised."""
    payload = payload or {}
    token = payload.get("token")
    items = payload.get("items") or []
    if MTS_ADMIN_TOKEN and token != MTS_ADMIN_TOKEN:
        return False, "forbidden"
    save_prompts_to_db(items)
    return True, "updated"

