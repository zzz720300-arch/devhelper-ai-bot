"""Inline keyboards used across handlers."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def lead_actions(order_id: str, profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить", callback_data=f"approve:{order_id}:{profile_id}")],
        [InlineKeyboardButton(text="Редактировать", callback_data=f"edit:{order_id}")],
        [InlineKeyboardButton(text="Пропустить", callback_data=f"skip:{order_id}")],
    ])


def result_actions(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить клиенту", callback_data=f"deliver:{order_id}")],
        [InlineKeyboardButton(text="Посмотреть лог", callback_data=f"log:{order_id}")],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"reject:{order_id}")],
    ])
