from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from app.modules.authn.consts import (
    MAX_REFRESH_TOKEN_LEN,
    MAX_RID_LEN,
    MAX_SECRET_LEN,
    REDIS_PREFIX_REFRESH,
    REDIS_PREFIX_TOKENVER,
    REFRESH_SEPARATOR,
)


@dataclass(frozen=True)  # refresh token拆分后的结构
class RefreshTokenPair:
    rid: str  # 用于redis key的随机uuid
    secret: str  # 用于验证的随机密钥，这里只存哈希，不存明文


_RE_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_RE_SAFE_SEG = re.compile(r"^[A-Za-z0-9._~-]+$")  # secret允许的字符集合


def _sha256(s: str) -> str:  # 计算sha256 hex，用于存储secret的哈希
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def mint_refresh_token() -> RefreshTokenPair:  # 生成一个新未入库的refresh token
    return RefreshTokenPair(rid=str(uuid.uuid4()), secret=secrets.token_urlsafe(48))


def pack_refresh(pair: RefreshTokenPair) -> str:  # 把rid和secret拼成refresh_token字符串给客户端保存
    return f"{pair.rid}{REFRESH_SEPARATOR}{pair.secret}"


def unpack_refresh(token: str) -> RefreshTokenPair:  # 从客户端传入的refresh_token解析出rid+secret并做严格校验
    if not isinstance(token, str):
        raise ValueError("bad_refresh_format")
    if len(token) == 0 or len(token) > int(MAX_REFRESH_TOKEN_LEN):
        raise ValueError("bad_refresh_format")
    if REFRESH_SEPARATOR not in token:
        raise ValueError("bad_refresh_format")

    rid, secret = token.split(REFRESH_SEPARATOR, 1)
    rid = rid.strip()
    secret = secret.strip()

    if not rid or not secret:
        raise ValueError("bad_refresh_format")
    if len(rid) > int(MAX_RID_LEN) or len(secret) > int(MAX_SECRET_LEN):
        raise ValueError("bad_refresh_format")

    if not _RE_UUID.match(rid):
        raise ValueError("bad_refresh_format")
    if not _RE_SAFE_SEG.match(secret):
        raise ValueError("bad_refresh_format")

    return RefreshTokenPair(rid=rid, secret=secret)


def key_refresh(rid: str) -> str:  # redis中refresh的key
    return f"{REDIS_PREFIX_REFRESH}{rid}"


def key_tokenver(user_id: int) -> str:  # redis中刷新tokenver的key
    return f"{REDIS_PREFIX_TOKENVER}{int(user_id)}" # auth:refresh:rid


def _decode_bytes(v):  # redis客户端可能返回bytes，这里做统一解码
    if isinstance(v, (bytes, bytearray)):
        try:
            return v.decode("utf-8")
        except Exception:
            return None
    return v


async def get_tokenver(redis, user_id: int) -> int:  # 获取某用户当前token version。不存在则0
    v = await redis.get(key_tokenver(int(user_id)))
    v = _decode_bytes(v)
    if v is None:
        return 0
    try:
        return int(v)
    except Exception:
        return 0


async def bump_tokenver(redis, user_id: int) -> int:  # tokenver自增，这里要踢掉所有旧access token
    return int(await redis.incr(key_tokenver(int(user_id))))


async def store_refresh(  # 把refresh token存到 redis，并设置TTL
    redis,
    *,
    pair: RefreshTokenPair,
    user_id: int,
    token_ver: int,
    ttl_days: int,
) -> None:
    val = f"{int(user_id)}|{int(token_ver)}|{_sha256(pair.secret)}"
    await redis.set(
        key_refresh(pair.rid),
        val.encode("utf-8"),
        ex=int(timedelta(days=int(ttl_days)).total_seconds()),
    )


async def revoke_refresh(redis, rid: str) -> None:  # 撤销某个refresh，即删除redis key
    await redis.delete(key_refresh(rid))

# LUA脚本，这里验证一个刷新令牌是否合理，若合理则消费refresh(删除)
# 之所以于此处使用LUA脚本，希望一次性验证并消费，避免出现无法消费的问题
_LUA_VERIFY_AND_CONSUME = """
local key = KEYS[1]
local want = ARGV[1]

local v = redis.call("GET", key)
if not v then
  return nil
end

local user_id, token_ver, secret_hash = string.match(v, "^(%d+)%|(%d+)%|(.+)$")
if not user_id then
  return nil
end

if secret_hash ~= want then
  return nil
end

redis.call("DEL", key)
return {user_id, token_ver}
"""


async def verify_and_consume_refresh(redis, *, pair: RefreshTokenPair) -> tuple[int, int] | None:
# 校验refresh token并消费掉
    want_hash = _sha256(pair.secret)
    res = await redis.eval(_LUA_VERIFY_AND_CONSUME, 1, key_refresh(pair.rid), want_hash)

    if not isinstance(res, (list, tuple)) or len(res) != 2:
        return None

    user_id = _decode_bytes(res[0])
    token_ver = _decode_bytes(res[1])

    try:
        return (int(user_id), int(token_ver))
    except Exception:
        return None