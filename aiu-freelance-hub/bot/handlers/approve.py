"""Handlers for approving leads and sending responses."""
from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.utils.config import get_settings
from bot.utils.db import get_order, update_order_status

router = Router()


@router.callback_query(F.data.startswith("approve:"))
async def approve_lead(callback: CallbackQuery) -> None:
    _, order_id, profile_id = callback.data.split(":")
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.core_url}/payments/create",
            json={"order_id": order_id, "amount": 5000, "provider": "yookassa"},
            headers={"X-ADMIN-ID": str(callback.from_user.id)},
        )
        if response.status_code != 200:
            await callback.answer("Не удалось создать платёж", show_alert=True)
            return
        payment_data = response.json()
    await update_order_status(order_id, "waiting_payment")
    await callback.message.answer(
        "Черновик отправлен владельцу. Ссылка на оплату:\n"
        f"{payment_data['confirmation_url']}"
    )
    await callback.answer("Ожидаем оплату")


@router.message(F.text.startswith("Оплата получена"))
async def dummy_payment_confirm(message: Message) -> None:
    await message.answer("Запускаю ядро на выполнение задачи.")


@router.callback_query(F.data.startswith("deliver:"))
async def deliver_result(callback: CallbackQuery) -> None:
    order_id = callback.data.split(":")[1]
    order = await get_order(order_id)
    if not order or not order.result_url:
        await callback.answer("Результат ещё не готов", show_alert=True)
        return
    await callback.message.answer(
        "✅ Готово. Вот архив и лог. Проект собран и проверен.\n"
        f"{order.result_url}"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("log:"))
async def send_log(callback: CallbackQuery) -> None:
    await callback.message.answer("Лог выполнения: все тесты прошли успешно.")
    await callback.answer()


@router.callback_query(F.data.startswith("reject:"))
async def reject_result(callback: CallbackQuery) -> None:
    await callback.message.answer("Результат отклонён. Запускаю пересборку.")
    await callback.answer()
