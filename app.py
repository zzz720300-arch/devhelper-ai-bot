"""Flask application entry point registering the MTS Analytics module."""
from __future__ import annotations

from flask import Flask, jsonify

from aiu_core.modules.mts_analytics.app import bp as mts_bp, demo_bp as mts_demo_bp

app = Flask(__name__)

# Register blueprints from the MTS Analytics module.
app.register_blueprint(mts_bp)
app.register_blueprint(mts_demo_bp)


@app.route("/")
def healthcheck() -> tuple:
    """Simple healthcheck endpoint."""
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=5000)

