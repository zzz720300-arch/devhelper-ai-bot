"""/start command handler."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.utils.config import get_settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    settings = get_settings()
    text = (
        "Здравствуйте, я инженер платформы AIU-CORE.\n"
        "Я собираю и проверяю задачи по направлениям Docker, Deploy и SQL-отчёты.\n"
        "Все результаты проходят тест и логирование.\n"
        f"Активные администраторы: {', '.join(str(admin) for admin in settings.admin_ids)}"
    )
    await message.answer(text)
