"""Configuration loader for bot and core shared settings."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    core_url: str = Field("http://localhost:8000", alias="CORE_URL")
    postgres_dsn: str = Field(..., alias="POSTGRES_DSN")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    yookassa_shop_id: str = Field(..., alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(..., alias="YOOKASSA_SECRET_KEY")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("admin_ids", pre=True)
    def _parse_admin_ids(cls, value):  # type: ignore[override]
        if isinstance(value, str):
            return [int(item) for item in value.split(",") if item.strip()]
        return value

    @property
    def admin_ids_set(self) -> set[int]:
        return {int(admin) for admin in self.admin_ids}


@lru_cache
def get_settings() -> Settings:
    return Settings()
