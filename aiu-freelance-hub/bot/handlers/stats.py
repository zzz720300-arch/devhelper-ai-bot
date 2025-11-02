"""Statistics handlers."""
from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select

from db.models import Complaint, Order, Payment, Profile
from db.session import session_scope

router = Router()


@router.message(Command("day"))
async def daily_stats(message: Message) -> None:
    today = datetime.utcnow() - timedelta(days=1)
    async with session_scope() as session:
        total_platforms = await session.execute(select(func.count(func.distinct(Order.source_platform))))
        total_found = await session.execute(select(func.count(Order.id)).where(Order.created_at >= today))
        total_sent = await session.execute(select(func.count(Order.id)).where(Order.status == "waiting_payment"))
        total_paid = await session.execute(select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)))
        total_errors = await session.execute(select(func.count(Order.id)).where(Order.status == "error"))
        total_complaints = await session.execute(select(func.count(Complaint.id)))

    platforms_count = total_platforms.scalar() or 0
    found_count = total_found.scalar() or 0
    sent_count = total_sent.scalar() or 0
    paid_row = total_paid.first() or (0, 0)
    paid_count, paid_amount = paid_row
    errors_count = total_errors.scalar() or 0
    complaints_count = total_complaints.scalar() or 0

    text = (
        "Площадок обработано: {platforms}\n"
        "Заказов найдено: {found}\n"
        "Отправлено: {sent}\n"
        "Оплачено: {paid} ({amount} ₽)\n"
        "Ошибок: {errors}\n"
        "Жалоб: {complaints}"
    ).format(
        platforms=platforms_count,
        found=found_count,
        sent=sent_count,
        paid=paid_count,
        amount=paid_amount,
        errors=errors_count,
        complaints=complaints_count,
    )
    await message.answer(text)


@router.message(Command("complaints"))
async def list_complaints_cmd(message: Message) -> None:
    async with session_scope() as session:
        result = await session.execute(select(Complaint).order_by(Complaint.created_at.desc()).limit(10))
        complaints = result.scalars().all()
    if not complaints:
        await message.answer("Активных жалоб нет.")
        return
    lines = [f"{complaint.created_at:%Y-%m-%d} — {complaint.reason}" for complaint in complaints]
    await message.answer("\n".join(lines))


@router.message(Command("profiles"))
async def list_profiles(message: Message) -> None:
    async with session_scope() as session:
        result = await session.execute(select(Profile).order_by(Profile.platform))
        profiles = result.scalars().all()
    lines = [
        f"{profile.platform}: {profile.profile_name} — {profile.specialty} ({'активен' if profile.active else 'остановлен'})"
        for profile in profiles
    ]
    await message.answer("\n".join(lines) if lines else "Профилей не найдено.")
