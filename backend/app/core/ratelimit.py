"""A lightweight in-process rate limiter.

Suitable for a single-instance deployment and development. For multi-instance
production, replace the backing store with Redis. Applied to sensitive/expensive
endpoints (auth, AI).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import AppError


class RateLimiter:
    def __init__(self, *, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_calls:
            raise AppError(
                "Too many requests. Please slow down and try again shortly.",
                status_code=429,
                code="rate_limited",
            )
        bucket.append(now)


def client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
