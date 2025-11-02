"""Entry point for Telegram bot operator."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from bot.handlers import approve, leads, start, stats
from bot.lead_collector import run_collector, seed_demo_data
from bot.utils.config import get_settings
from db.models import Base
from db.session import create_all, init_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    settings = get_settings()
    init_engine(settings.postgres_dsn)
    await create_all(Base.metadata)
    await seed_demo_data()
    sources_file = Path(__file__).resolve().parent / "sources.json"
    asyncio.create_task(run_collector(sources_file))
    logger.info("Lead collector started")


async def main() -> None:
    settings = get_settings()
    init_engine(settings.postgres_dsn)
    await create_all(Base.metadata)

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(leads.router)
    dp.include_router(approve.router)
    dp.include_router(stats.router)

    dp.startup.register(on_startup)

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
