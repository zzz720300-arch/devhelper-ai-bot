"""Process routes for executing tasks."""
from __future__ import annotations

import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.handlers import docker_handler, deploy_handler, report_handler
from core.main import STORAGE_PATH
from db.models import Order
from db.session import session_scope

router = APIRouter()

TASK_HANDLERS = {
    "docker": docker_handler.generate_archive,
    "deploy": deploy_handler.generate_archive,
    "report": report_handler.generate_archive,
}


class ProcessRequest(BaseModel):
    order_id: uuid.UUID = Field(..., description="Order identifier")
    task_type: str = Field(..., pattern="^(docker|deploy|report)$")
    payload: Dict[str, str] | None = None


class ProcessResponse(BaseModel):
    order_id: uuid.UUID
    status: str
    result_url: str


@router.post("/run", response_model=ProcessResponse)
async def run_process(request: ProcessRequest) -> ProcessResponse:
    handler = TASK_HANDLERS.get(request.task_type)
    if not handler:
        raise HTTPException(status_code=400, detail="Unsupported task type")

    async with session_scope() as session:
        order = await session.get(Order, request.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order.status = "processing"
        await session.flush()

    filename, content = await handler(str(request.order_id))
    target = STORAGE_PATH / filename
    target.write_bytes(content)
    result_url = f"/storage/{filename}"

    async with session_scope() as session:
        order = await session.get(Order, request.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found after processing")
        order.status = "done"
        order.result_url = result_url
        await session.flush()

    return ProcessResponse(order_id=request.order_id, status="done", result_url=result_url)
