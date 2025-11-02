"""Core statistics endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from db.models import Complaint, Order, Payment
from db.session import session_scope

router = APIRouter()


class StatsResponse(BaseModel):
    orders_found: int
    orders_done: int
    payments_total: float
    complaints: int


@router.get("/daily", response_model=StatsResponse)
async def get_daily_stats() -> StatsResponse:
    since = datetime.utcnow() - timedelta(days=1)
    async with session_scope() as session:
        found = await session.execute(select(func.count(Order.id)).where(Order.created_at >= since))
        done = await session.execute(select(func.count(Order.id)).where(Order.status == "done"))
        payments = await session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.created_at >= since)
        )
        complaints = await session.execute(select(func.count(Complaint.id)).where(Complaint.created_at >= since))

    return StatsResponse(
        orders_found=found.scalar() or 0,
        orders_done=done.scalar() or 0,
        payments_total=float(payments.scalar() or 0),
        complaints=complaints.scalar() or 0,
    )
