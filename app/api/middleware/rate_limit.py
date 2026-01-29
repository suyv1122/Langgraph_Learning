from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Request
from redis.exceptions import RedisError

from app.core.errors import raise_err
from app.infra.redis_client import get_redis
from app.api.middleware.real_ip import get_real_ip
from app.modules.audit.hook import record

RL_REDIS_KEY_PREFIX = "rl"


@dataclass(frozen=True)
class RateLimitSpec:
    name: str
    limit: int
    window_seconds: int


def _key_fixed_window(prefix: str, identifier: str, window_seconds: int, now_ts: int) -> str:
    bucket = now_ts // window_seconds
    return f"{RL_REDIS_KEY_PREFIX}:{prefix}:{identifier}:{bucket}"


def _to_int(v: object) -> int | None:
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        try:
            v = v.decode("utf-8")
        except UnicodeDecodeError:
            return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def rate_limit_ip(spec: RateLimitSpec) -> Callable:
    async def _dep(request: Request, redis=Depends(get_redis)):
        ip = get_real_ip(request) or "unknown"
        now = int(time.time())
        k = _key_fixed_window(spec.name, ip, int(spec.window_seconds), now)

        n_raw = await redis.incr(k)
        n = _to_int(n_raw)
        if n is None:
            raise_err("error.internal", meta={"where": "rate_limit", "reason": "bad_redis_incr"})

        if n == 1:
            ttl = int(spec.window_seconds)
            if ttl <= 0:
                raise_err("error.internal", meta={"where": "rate_limit", "reason": "bad_window_seconds"})
            try:
                await redis.expire(k, ttl)
            except RedisError:
                try:
                    await redis.delete(k)
                except RedisError:
                    raise_err("error.internal", meta={"where": "rate_limit", "reason": "redis_expire_failed"})

        if n > int(spec.limit):
            record(
                action="http.rate_limited",
                status="deny",
                http_status=429,
                meta={"name": spec.name, "limit": int(spec.limit), "window_seconds": int(spec.window_seconds), "ip": ip},
                error_code="error.rate_limited",
            )
            raise_err(
                "error.rate_limited",
                meta={"name": spec.name, "limit": int(spec.limit), "window_seconds": int(spec.window_seconds)},
            )

    return _dep