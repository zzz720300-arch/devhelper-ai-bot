"""Blueprints for the MTS Analytics module."""
from __future__ import annotations

import time
from flask import Blueprint, jsonify, render_template_string, request

from .service import handle_query, list_prompts, update_prompts

# API blueprint -------------------------------------------------------------

bp = Blueprint("mts_analytics_api", __name__, url_prefix="/api/mts-analytics")


@bp.route("/query", methods=["POST"])
def query() -> tuple:
    """Process an analytics query from the client."""
    started = time.time()
    try:
        payload = request.get_json(force=True)
    except Exception:  # pragma: no cover - defensive guard
        return jsonify({"status": "error", "error": "invalid json"}), 400

    result = handle_query(payload)
    result["duration_ms"] = int((time.time() - started) * 1000)
    return jsonify(result), 200


@bp.route("/prompts", methods=["GET"])
def get_prompts() -> tuple:
    """Return the configured prompts."""
    items = list_prompts()
    return jsonify({"status": "ok", "items": items}), 200


@bp.route("/prompts", methods=["POST"])
def post_prompts() -> tuple:
    """Update prompts stored in the database."""
    payload = request.get_json(force=True)
    ok, msg = update_prompts(payload)
    return jsonify({"status": "ok" if ok else "error", "message": msg}), 200


# Demo blueprint ------------------------------------------------------------

demo_bp = Blueprint("mts_analytics_demo", __name__)

DEMO_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>MTS Analytics — LLM-агент</title>
  <style>
    body { font-family: sans-serif; max-width: 780px; margin: 28px auto; }
    #log { border: 1px solid #ddd; height: 360px; overflow-y: auto; padding: 10px; margin-bottom: 14px; }
    .msg { margin-bottom: 8px; padding: 8px 10px; border-radius: 8px; }
    .user { background: #dcefff; text-align: right; }
    .bot { background: #f3f3f3; }
    input { font-size: 16px; }
    button { font-size: 16px; }
  </style>
</head>
<body>
  <h2>MTS Analytics — демо агента</h2>
  <p>Задайте вопрос, например: «Сгенерируй SQL по абонентам МСК за последний месяц» или «Придумай промт для классификации обращений в поддержку».</p>
  <div id="log"></div>
  <input id="text" style="width:78%" placeholder="ваш запрос..." />
  <button onclick="send()">Отправить</button>
  <script>
    const log = document.getElementById('log');
    const sid = 'web-mts-demo';
    function addMsg(text, cls) {
      const d = document.createElement('div');
      d.className = 'msg ' + cls;
      d.textContent = text;
      log.appendChild(d);
      log.scrollTop = log.scrollHeight;
    }
    async function send() {
      const v = document.getElementById('text').value;
      if (!v) return;
      addMsg(v, 'user');
      document.getElementById('text').value = '';
      const resp = await fetch('/api/mts-analytics/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          session_id: sid,
          user_query: v,
          meta: {"channel": "web", "lang": "ru"}
        })
      });
      const data = await resp.json();
      addMsg(data.answer || '[нет ответа]', 'bot');
    }
  </script>
</body>
</html>
"""


@demo_bp.route("/mts-analytics", methods=["GET"])
def mts_page() -> str:
    """Render the demo chat page."""
    return render_template_string(DEMO_HTML)

