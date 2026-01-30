from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.rate_limit import RateLimitSpec, rate_limit_ip
from app.api.response import ok_no_store
from app.core.api_schemas import ActionResult, ApiResponse
from app.core.config import settings
from app.core.errors import raise_err
from app.infra.db.deps import get_db
from app.infra.redis_client import get_redis
from app.modules.audit.hook import record
from app.modules.auth.models import User
from app.modules.authn.consts import RL_AUTH_LOGIN, RL_AUTH_REFRESH, RL_AUTH_REGISTER
from app.modules.authn.deps import get_current_user
from app.modules.authn.schemas import LoginReq, MeResp, RefreshReq, RegisterReq, TokenResp
from app.modules.authn.service import (
    bump_tokenver,
    get_tokenver,
    mint_refresh_token,
    pack_refresh,
    revoke_refresh,
    store_refresh,
    unpack_refresh,
    verify_and_consume_refresh,
)
from app.modules.security.jwt import create_access_token
from app.modules.security.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


async def _noop_dep() -> None:  # 当限流关闭时，用这个空依赖替代限流依赖，保持routes写法不变。
    return None


def _auth_rl(name: str):  # 生成按IP限流的依赖函数，name参数用来区分不同接口的限流桶
    if not settings.rate_limit_enabled:
        return _noop_dep
    return rate_limit_ip(  # 返回一个Depends依赖，用来固定窗口计数，超过抛429
        RateLimitSpec(
            name=name,
            limit=settings.auth_rate_limit_per_window,
            window_seconds=settings.auth_rate_limit_window_seconds,
        )
    )


_rl_register = _auth_rl(RL_AUTH_REGISTER)  # 注册接口限流依赖
_rl_login = _auth_rl(RL_AUTH_LOGIN)  # 登录接口限流依赖
_rl_refresh = _auth_rl(RL_AUTH_REFRESH)  # # 刷新接口限流依赖


@router.post(
    "/register",
    response_model=ApiResponse[MeResp],
    status_code=201,
    dependencies=[Depends(_rl_register)],
)
async def register(req: RegisterReq, response: Response, db: AsyncSession = Depends(get_db)):
    async with db.begin_nested():  # 事务打开
        exists = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()  # 根据结果数量返回不同内容
        if exists:
            record(
                action="auth.register",
                status="deny",
                http_status=409,
                meta={"reason": "email_taken", "email": str(req.email)},
            )
            raise_err("auth.email_taken")

        user = User(email=req.email, password_hash=hash_password(req.password))
        db.add(user)  # 加入session
        await db.flush()  # user.id生成postgres的identity或者sequence
        await db.refresh(user)  # refresh把数据库生成字段回填到orm对象

    record(
        action="auth.register",
        status="ok",
        actor_user_id=int(user.id),
        meta={"user_id": int(user.id), "email": str(user.email)},
    )

    data = MeResp(
        id=int(user.id),
        email=user.email,
        is_active=bool(user.is_active),
        is_superadmin=bool(user.is_superadmin),
    )
    return ok_no_store(response, data)


@router.post(
    "/login",
    response_model=ApiResponse[TokenResp],
    dependencies=[Depends(_rl_login)],
)
async def login(
    req: LoginReq,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not user or not bool(user.is_active):
        record(action="auth.login", status="deny", http_status=401, meta={"email": str(req.email)})
        raise_err("auth.credentials_invalid")
    if not verify_password(req.password, user.password_hash):
        record(action="auth.login", status="deny", http_status=401, meta={"email": str(req.email)})
        raise_err("auth.credentials_invalid")

    token_ver = await bump_tokenver(redis, int(user.id))  # token version自增，让所有旧的access token立即失效，这里全端踢下线
    token_ver = int(token_ver)

    access = create_access_token(  # 生成短期访问令牌
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        alg=settings.jwt_alg.value,
        user_id=int(user.id),
        token_ver=int(token_ver),
        minutes=settings.access_token_expire_minutes,
    )

    pair = mint_refresh_token()  # 这里生成刷新令牌
    await store_refresh(  # 然后将刷新令牌存入redis，存入的是user_id|token_ver|sha256(secret)这个东西
        redis,
        pair=pair,
        user_id=int(user.id),
        token_ver=int(token_ver),
        ttl_days=settings.refresh_token_expire_days,
    )

    record(action="auth.login", status="ok", actor_user_id=int(user.id), meta={"user_id": int(user.id)})

    data = TokenResp(  # 返回access和refresh
        access_token=access,
        expires_in_minutes=settings.access_token_expire_minutes,
        refresh_token=pack_refresh(pair),
    )
    return ok_no_store(response, data)


@router.post(  # 刷新，主要是refresh token校验和消费一次性完成，然后颁发新的access和新的refresh
    "/refresh",
    response_model=ApiResponse[TokenResp],
    dependencies=[Depends(_rl_refresh)],
)
async def refresh(
    req: RefreshReq,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    try:
        pair = unpack_refresh(req.refresh_token)
    except Exception:
        record(action="auth.refresh", status="deny", http_status=401, meta={"reason": "bad_format"})
        raise_err("auth.refresh_token_invalid")

    consumed = await verify_and_consume_refresh(redis, pair=pair)
    # redis lua脚本，主要是校验secret_hash匹配后在删除rid，主打一次性消费
    if not consumed:
        record(action="auth.refresh", status="deny", http_status=401, meta={"reason": "not_found_or_mismatch"})
        raise_err("auth.refresh_token_invalid")

    user_id, token_ver = consumed  # 从redis值里取出user_id和token_ver

    current_ver = await get_tokenver(redis, int(user_id))  # 再读取当前tokenver，确保refresh对应的版本仍有效
    if int(token_ver) != int(current_ver):
        record(
            action="auth.refresh",
            status="deny",
            http_status=401,
            meta={"reason": "tokenver_mismatch", "user_id": int(user_id)},
        )
        raise_err("auth.refresh_token_expired")

    user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    # 读取用户实体，避免refresh对应用户被禁用仍能换新token
    if not user or not bool(user.is_active):
        record(
            action="auth.refresh",
            status="deny",
            http_status=401,
            meta={"reason": "user_inactive", "user_id": int(user_id)},
        )
        raise_err("auth.user_inactive")

    access = create_access_token(  # 生成新的access token
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        alg=settings.jwt_alg.value,
        user_id=int(user_id),
        token_ver=int(token_ver),
        minutes=settings.access_token_expire_minutes,
    )

    new_pair = mint_refresh_token()  # 生成新的refresh，一次刷新发一次新refresh
    await store_refresh(  # 生成新的refresh，一次刷新发一次新refresh
        redis,
        pair=new_pair,
        user_id=int(user_id),
        token_ver=int(token_ver),
        ttl_days=settings.refresh_token_expire_days,
    )

    record(action="auth.refresh", status="ok", actor_user_id=int(user_id), meta={"user_id": int(user_id)})

    data = TokenResp(  # 返回新的access + refresh
        access_token=access,
        expires_in_minutes=settings.access_token_expire_minutes,
        refresh_token=pack_refresh(new_pair),
    )
    return ok_no_store(response, data)


@router.post("/logout", response_model=ApiResponse[ActionResult])
# 注销，这里尽量撤销当前refresh），并bump tokenver让所有旧access失效
async def logout(
    req: RefreshReq,
    response: Response,
    redis=Depends(get_redis),
    me: User = Depends(get_current_user),
):
    try:
        pair = unpack_refresh(req.refresh_token)
        await revoke_refresh(redis, pair.rid)  #  删除对应rid的redis key
    except Exception:
        pass  # 登出尽量幂等，refresh不对也不影响继续登出流程

    await bump_tokenver(redis, int(me.id))  # tokenver自增，这样该用户所有旧access token立即失效
    record(action="auth.logout", status="ok", meta={"user_id": int(me.id)})
    return ok_no_store(response, ActionResult(ok=True))


@router.get("/me", response_model=ApiResponse[MeResp])
async def me(response: Response, user: User = Depends(get_current_user)):
    record(action="auth.me", status="ok", meta={"user_id": int(user.id)})
    data = MeResp(
        id=int(user.id),
        email=user.email,
        is_active=bool(user.is_active),
        is_superadmin=bool(user.is_superadmin),
    )
    return ok_no_store(response, data)