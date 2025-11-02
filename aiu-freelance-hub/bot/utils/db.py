"""Helpers for interacting with the database from the bot."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, update

from db.models import Complaint, Order, Payment, Profile
from db.session import session_scope


async def fetch_active_profiles() -> List[Profile]:
    async with session_scope() as session:
        result = await session.execute(select(Profile).where(Profile.active.is_(True)))
        return list(result.scalars().all())


async def create_order(order: Order) -> Order:
    async with session_scope() as session:
        session.add(order)
        await session.flush()
        await session.refresh(order)
        return order


async def update_order_status(order_id, status: str) -> None:
    async with session_scope() as session:
        await session.execute(update(Order).where(Order.id == order_id).values(status=status))


async def get_order(order_id) -> Optional[Order]:
    async with session_scope() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        return result.scalars().first()


async def list_orders(limit: int = 20) -> List[Order]:
    async with session_scope() as session:
        result = await session.execute(select(Order).order_by(Order.created_at.desc()).limit(limit))
        return list(result.scalars().all())


async def list_complaints(limit: int = 20) -> List[Complaint]:
    async with session_scope() as session:
        result = await session.execute(select(Complaint).order_by(Complaint.created_at.desc()).limit(limit))
        return list(result.scalars().all())


async def list_payments(limit: int = 20) -> List[Payment]:
    async with session_scope() as session:
        result = await session.execute(select(Payment).order_by(Payment.created_at.desc()).limit(limit))
        return list(result.scalars().all())
