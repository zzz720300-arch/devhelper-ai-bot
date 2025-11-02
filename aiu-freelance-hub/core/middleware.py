"""FastAPI middleware for rate limiting."""
from __future__ import annotations

import time
from collections import deque
from typing import Deque

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter."""

    def __init__(self, app, per_minute: int = 4, per_day: int = 3000) -> None:
        super().__init__(app)
        self.per_minute = per_minute
        self.per_day = per_day
        self.minute_calls: Deque[float] = deque()
        self.daily_calls: Deque[float] = deque()

    async def dispatch(self, request: Request, call_next):
        now = time.time()
        minute_cutoff = now - 60
        day_cutoff = now - 86400

        while self.minute_calls and self.minute_calls[0] < minute_cutoff:
            self.minute_calls.popleft()
        while self.daily_calls and self.daily_calls[0] < day_cutoff:
            self.daily_calls.popleft()

        if len(self.minute_calls) >= self.per_minute:
            raise HTTPException(status_code=429, detail="Too many requests per minute. Order queued.")
        if len(self.daily_calls) >= self.per_day:
            raise HTTPException(status_code=429, detail="Daily limit exceeded. Order queued.")

        self.minute_calls.append(now)
        self.daily_calls.append(now)

        response = await call_next(request)
        return response
