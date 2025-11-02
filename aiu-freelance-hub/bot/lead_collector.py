"""Lead collector that polls sources and creates orders."""
from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Iterable, List

from sqlalchemy import select

from db.models import Order, Profile
from db.session import session_scope

KEYWORDS = {
    "docker": ["docker", "compose", "container"],
    "deploy": ["deploy", "nginx", "ssl", "service"],
    "report": ["excel", "csv", "report", "sql"],
}

logger = logging.getLogger(__name__)


async def _load_sources(file_path: Path) -> Iterable[dict]:
    if not file_path.exists():
        return []
    try:
        data = json.loads(file_path.read_text("utf-8"))
        return data.get("items", [])
    except Exception as exc:  # pragma: no cover - only used during runtime
        logger.exception("Failed to load sources: %s", exc)
        return []


def _match_task_type(description: str) -> str | None:
    lowered = description.lower()
    for task_type, words in KEYWORDS.items():
        if any(word in lowered for word in words):
            return task_type
    return None


async def _pick_profile(task_type: str) -> Profile | None:
    async with session_scope() as session:
        result = await session.execute(select(Profile).where(Profile.active.is_(True)))
        profiles: List[Profile] = list(result.scalars().all())
        if not profiles:
            return None
        candidates = [profile for profile in profiles if task_type in profile.specialty.lower()]
        return random.choice(candidates or profiles)


async def _create_order(data: dict, task_type: str, profile: Profile | None) -> Order:
    order = Order(
        source_platform=data.get("platform", "unknown"),
        source_link=data.get("link"),
        customer_contact=data.get("contact"),
        title=data.get("title", "Без названия"),
        description=data.get("description", ""),
        matched_profile_id=profile.id if profile else None,
        task_type=task_type,
        status="found",
        price=data.get("price"),
    )
    async with session_scope() as session:
        session.add(order)
        await session.flush()
        await session.refresh(order)
        return order


async def _order_exists(source_link: str | None) -> bool:
    if not source_link:
        return False
    async with session_scope() as session:
        result = await session.execute(select(Order.id).where(Order.source_link == source_link))
        return result.scalars().first() is not None


async def collect_once(sources_file: Path) -> List[Order]:
    collected: List[Order] = []
    for item in await asyncio.to_thread(lambda: list(_load_sources(sources_file))):
        description = item.get("description", "")
        task_type = _match_task_type(description)
        if not task_type:
            continue
        if await _order_exists(item.get("link")):
            continue
        profile = await _pick_profile(task_type)
        order = await _create_order(item, task_type, profile)
        logger.info("Collected new order %s", order.id)
        collected.append(order)
    return collected


async def run_collector(sources_file: Path, interval: tuple[int, int] = (60, 180)) -> None:
    while True:
        await collect_once(sources_file)
        await asyncio.sleep(random.randint(*interval))


async def seed_demo_data() -> None:
    """Populate initial profiles for demo."""
    async with session_scope() as session:
        result = await session.execute(select(Profile))
        if result.scalars().first():
            return
        profiles = [
            Profile(platform="Freelance.ru", profile_name="Максим К.", specialty="python docker",
                    tone={"greeting": "Здравствуйте", "style": "инженер AIU-OPS"}, contact="https://freelance.ru/max"),
            Profile(platform="Kwork.ru", profile_name="Анна М.", specialty="deploy devops",
                    tone={"greeting": "Добрый день", "style": "DevOps"}, contact="https://kwork.ru/user/anna"),
            Profile(platform="Habr Freelance", profile_name="AIU Data",
                    specialty="report sql data", tone={"greeting": "Здравствуйте", "style": "аналитик"},
                    contact="https://freelance.habr.com/aiu-data"),
        ]
        session.add_all(profiles)
        await session.flush()
        logger.info("Seeded demo profiles")
