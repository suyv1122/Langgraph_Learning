# 这段代码在项目启动之前作为一次性的检测脚本，只运行一次，通过了项目就可以启动了
from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.config import settings
from app.core.enums import Env

logger = logging.getLogger(__name__)


def _is_prod() -> bool:  # 是不是生产环境/上线了
    return settings.env in {Env.prod, Env.production}


async def run_startup_checks(app) -> None:
    prod = _is_prod()

    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        msg = "weak_jwt_secret"
        extra = {"min_len": 32, "env": str(settings.env)}
        if prod:
            raise RuntimeError(f"{msg}: {extra}")
        logger.warning(msg, extra=extra)

    if settings.cors_allow_credentials and (settings.cors_allow_origins or "").strip() == "*":
        msg = "cors_invalid_credentials_with_wildcard_origin"
        extra = {"env": str(settings.env)}
        if prod:
            raise RuntimeError(f"{msg}: {extra}")
        logger.warning(msg, extra=extra)

    await app.state.redis.ping()

    session_maker = app.state.db_session_maker
    async with session_maker() as session:
        await session.execute(text("SELECT 1"))

    ok = await app.state.es.ping()
    if not ok:
        raise RuntimeError("elasticsearch_ping_failed")

