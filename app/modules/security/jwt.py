from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.modules.security.jwt_claims import (
    CLAIM_EXP,
    CLAIM_IAT,
    CLAIM_ISS,
    CLAIM_SUB,
    CLAIM_TYP,
    CLAIM_VER,
    TOKEN_TYPE_ACCESS,
)


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    token_ver: int
    typ: str


def create_access_token(
    *,
    secret: str,
    issuer: str,
    alg: str,
    user_id: int,
    token_ver: int,
    minutes: int,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        CLAIM_ISS: str(issuer),
        CLAIM_SUB: str(int(user_id)),
        CLAIM_VER: int(token_ver),
        CLAIM_TYP: TOKEN_TYPE_ACCESS,
        CLAIM_IAT: int(now.timestamp()),
        CLAIM_EXP: int((now + timedelta(minutes=int(minutes))).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=str(alg))


def _must_int(payload: dict[str, Any], k: str) -> int:
# 确定载荷中是放的int，此处是用户id，即int类型
    v = payload.get(k)
    if v is None:
        raise ValueError("invalid_token_payload")
    try:
        return int(v)
    except Exception as e:
        raise ValueError("invalid_token_payload") from e


def decode_access_token(
    *,
    token: str,
    secret: str,
    issuer: str,
    alg: str,
    leeway_seconds: int = 30,
) -> TokenPayload:
    try:
        options = {
            "verify_aud": False,
            "require_exp": True,
            "require_sub": True,
            "require_iss": True,
            "leeway": int(leeway_seconds),
        }
        payload = jwt.decode(
            token,
            secret,
            algorithms=[str(alg)],
            issuer=str(issuer),
            options=options,
        )
    except JWTError as e:
        raise ValueError("invalid_token") from e

    if not isinstance(payload, dict):
        raise ValueError("invalid_token_payload")

    if payload.get(CLAIM_TYP) != TOKEN_TYPE_ACCESS:
        raise ValueError("invalid_token_type")

    user_id = _must_int(payload, CLAIM_SUB)
    token_ver = _must_int(payload, CLAIM_VER)

    iat = payload.get(CLAIM_IAT)
    if iat is None:
        raise ValueError("invalid_token_payload")

    return TokenPayload(user_id=int(user_id), token_ver=int(token_ver), typ=TOKEN_TYPE_ACCESS)
