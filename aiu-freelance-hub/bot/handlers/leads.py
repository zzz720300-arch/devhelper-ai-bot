"""Handlers related to new leads."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.utils import keyboards
from bot.utils.db import list_orders

router = Router()


@router.message(Command("leads"))
async def list_recent_leads(message: Message) -> None:
    orders = await list_orders()
    if not orders:
        await message.answer("Новых заказов нет. Мониторю площадки каждые 2 минуты.")
        return
    for order in orders:
        text = (
            "🆕 Новый заказ\n"
            f"Площадка: {order.source_platform}\n"
            f"Тема: {order.title}\n"
            f"Описание: {order.description[:300]}...\n"
            f"Цена: {order.price or '—'}\n"
            f"Статус: {order.status}"
        )
        keyboard = keyboards.lead_actions(str(order.id), order.matched_profile_id or 0)
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("skip:"))
async def skip_lead(callback: CallbackQuery) -> None:
    await callback.answer("Пропущено")


@router.callback_query(F.data.startswith("edit:"))
async def edit_lead(callback: CallbackQuery) -> None:
    await callback.message.answer("Черновик можно скорректировать вручную. Введите новый текст ответа.")
    await callback.answer()
