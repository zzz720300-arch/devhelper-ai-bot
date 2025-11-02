"""FastAPI application for AIU-FREELANCE-HUB core."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from bot.utils.config import get_settings
from core.middleware import RateLimitMiddleware
from core.routes import payments, process, stats
from db.models import Base
from db.session import create_all, init_engine

STORAGE_PATH = Path("storage")


def create_app() -> FastAPI:
    app = FastAPI(title="AIU-FREELANCE-HUB Core", version="1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    app.include_router(process.router, prefix="/process", tags=["process"])
    app.include_router(payments.router, prefix="/payments", tags=["payments"])
    app.include_router(stats.router, prefix="/stats", tags=["stats"])

    STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=STORAGE_PATH), name="storage")

    @app.on_event("startup")
    async def startup_event() -> None:
        settings = get_settings()
        init_engine(settings.postgres_dsn)
        await create_all(Base.metadata)
        STORAGE_PATH.mkdir(parents=True, exist_ok=True)

    return app


app = create_app()
