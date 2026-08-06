"""
app/cache/redis_client.py — Async Redis client with connection pool.
"""

from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = await aioredis.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised. Call init_redis() first.")
    return _redis


# ── Helpers ───────────────────────────────────────────────────────────────

async def cache_set(key: str, value: str, ttl: int | None = None) -> None:
    r = get_redis()
    await r.set(key, value, ex=ttl or settings.session_ttl_seconds)


async def cache_get(key: str) -> Optional[str]:
    return await get_redis().get(key)


async def cache_delete(key: str) -> None:
    await get_redis().delete(key)


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a glob pattern. Returns count deleted."""
    r = get_redis()
    keys = await r.keys(pattern)
    if keys:
        return await r.delete(*keys)
    return 0
