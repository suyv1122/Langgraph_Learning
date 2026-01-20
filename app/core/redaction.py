from __future__ import annotations

import re
from typing import Any

_RE_BEARER = re.compile(r"\bBearer\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE)
# 用于匹配Bearer <token>的正则：

_RE_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+=*\.[A-Za-z0-9_-]+=*\.[A-Za-z0-9_-]+=*\b")
# 用于匹配JWT的粗略正则，JWT通常以eyJ开头，三段.分割


SENSITIVE_KEYS = {  # 敏感字段key的集合，当dict的key命中这些名字时，对应value会被替换成***
    "password",
    "passwd",
    "secret",
    "jwt",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
}

def redact_str(s: str) -> str:   # redact_str对字符串做脱敏
    # 把Bearer token替换为固定文本
    s = _RE_BEARER.sub("Bearer ***", s)

    # 把JWT替换成***.***.*** 形式
    s = _RE_JWT.sub("***.***.***", s)

    return s

def redact_obj(obj: Any) -> Any:
    # redact_obj对任意对象做递归脱敏
    if obj is None:
        return None

    # 如果参数是字符串，则应用redact_str
    if isinstance(obj, str):
        return redact_str(obj)

    # 基础标量，不需要脱敏原样返回
    if isinstance(obj, (int, float, bool)):
        return obj

    # list逐个元素递归脱敏
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]

    # tuple逐个元素递归脱敏后再转回tuple
    if isinstance(obj, tuple):
        return tuple(redact_obj(x) for x in obj)

    # dict对key做敏感字段判断，对value递归脱敏
    if isinstance(obj, dict):
        out: dict[Any, Any] = {}
        for k, v in obj.items():
            kk = k

            # 只有key是str才做敏感字段判断，避免把非字符串key强行lower导致异常
            if isinstance(kk, str):
                # 统一用小写比较，避免Password/password等大小写差异
                kl = kk.lower()

                # 命中敏感key直接把value替换成***
                if kl in SENSITIVE_KEYS:
                    out[kk] = "***"
                    continue

            # 未命中敏感key：递归脱敏value
            out[kk] = redact_obj(v)

        # 返回脱敏后的dict
        return out

    # 其他未知类型直接返回原对象不做处理
    return obj
