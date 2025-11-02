"""Docker task handler."""
from __future__ import annotations

import io
import zipfile
from typing import Tuple


DOCKER_TEMPLATE = """FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
CMD [\"python\", \"main.py\"]
"""

COMPOSE_TEMPLATE = """version: '3.9'
services:
  app:
    build: .
    ports:
      - "8000:8000"
"""

REQUIREMENTS_TEMPLATE = """fastapi==0.111.0
uvicorn[standard]==0.29.0
"""

MAIN_TEMPLATE = """from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok"}
"""


async def generate_archive(order_id: str) -> Tuple[str, bytes]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Dockerfile", DOCKER_TEMPLATE)
        archive.writestr("docker-compose.yml", COMPOSE_TEMPLATE)
        archive.writestr("requirements.txt", REQUIREMENTS_TEMPLATE)
        archive.writestr("main.py", MAIN_TEMPLATE)
    buffer.seek(0)
    filename = f"docker-package-{order_id}.zip"
    return filename, buffer.getvalue()
