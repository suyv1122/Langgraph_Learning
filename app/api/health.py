# 这个代码是项目启动后，每隔一段时间或者利用外部工具来检测项目本身、中间件是否正常而使用的
from __future__ import annotations

from fastapi import APIRouter, Request
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.api_response import ok
from app.core.api_schemas import ApiResponse
from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/healthz", response_model=ApiResponse[dict])
async def healthz():
    return ok({"ok": True})


@router.get("/readyz", response_model=ApiResponse[dict])
async def readyz(request: Request):
    db_ok = False
    redis_ok = False
    es_ok = False

    try:
        session_maker = request.app.state.db_session_maker
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except (AttributeError, SQLAlchemyError):
        pass

    try:
        redis = request.app.state.redis
        await redis.ping()
        redis_ok = True
    except (AttributeError, RedisError, TimeoutError, OSError):
        pass

    try:
        es = request.app.state.es
        es_ok = bool(await es.ping())
    except Exception:
        es_ok = False

    ok_all = bool(db_ok and redis_ok and es_ok)
    return ok({"ok": ok_all, "deps": {"db": db_ok, "redis": redis_ok, "es": es_ok}})


@router.get("/version", response_model=ApiResponse[dict])
async def version():
    return ok({"app": settings.app_name, "env": settings.env})