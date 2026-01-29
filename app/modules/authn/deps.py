from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import raise_err
from app.core.request_context import set_user_id
from app.infra.db.deps import get_db
from app.infra.redis_client import get_redis
from app.modules.audit.hook import record
from app.modules.auth.models import User
from app.modules.authn.service import get_tokenver
from app.modules.security.jwt import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)
# 定义Bearer认证解析器auto_error=False表示没有token时不自动抛403，由我们自己手工处理

async def get_current_user(  # 获取当前登录用户
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    if creds is None or not creds.credentials:
        record(action="auth.bearer_required", status="deny", http_status=401, meta={"where": "get_current_user"})
        raise_err("auth.bearer_required")

    token = creds.credentials

    try:
        payload = decode_access_token(
            token=token,
            secret=settings.jwt_secret,
            issuer=settings.jwt_issuer,
            alg=settings.jwt_alg.value,
        )
    except ValueError:
        record(action="auth.access_token_invalid", status="deny", http_status=401, meta={"where": "get_current_user"})
        raise_err("auth.access_token_invalid")

    current_ver = await get_tokenver(redis, payload.user_id)
    if int(payload.token_ver) != int(current_ver):
        record(
            action="auth.access_token_expired",
            status="deny",
            http_status=401,
            meta={"where": "get_current_user", "user_id": int(payload.user_id)},
        )
        raise_err("auth.access_token_expired")

    user = (await db.execute(select(User).where(User.id == payload.user_id))).scalar_one_or_none()
    if not user or not bool(user.is_active):
        record(
            action="auth.user_inactive",
            status="deny",
            http_status=401,
            meta={"where": "get_current_user", "user_id": int(payload.user_id)},
        )
        raise_err("auth.user_inactive")

    set_user_id(int(user.id))
    return user
