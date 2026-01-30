# 1.6
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, NoReturn
from app.core.error_codes import ERROR_MESSAGES, ERROR_STATUS

@dataclass
class AppError(Exception):  # 业务错误的统一异常类型
    code: str
    http_status: int = 400   # HTTP状态码，默认400
    message: str | None = None
    meta: dict[str, Any] | None = None  # 结构化上下文信息

    # dataclass 初始化后会调用 __post_init__
    # 这里显式调用 Exception.__init__，确保异常 message 正常出现在 str(exc) 里
    def __post_init__(self) -> None:
        Exception.__init__(self, self.message or self.code)

def resolve_message(code: str, default: str | None = None) -> str:
    # 给错误码解析默认 message
    c = str(code or "").strip()

    if not c:
        return str(default or "")

    msg = ERROR_MESSAGES.get(c)

    if msg is not None:
        return str(msg)

    # 查不到则回退到default或code本身
    return str(default or c)



def err(  # 构造一个AppError实例但不抛出
    code: str,
    *,
    http_status: int | None = None,
    message: str | None = None,
    meta: Mapping[str, Any] | None = None,
) -> AppError:
    c = str(code)

    # 如果显式传了http_status，用它；否则从ERROR_STATUS里取默认；再否则默认400
    st = int(http_status) if http_status is not None else int(ERROR_STATUS.get(c, 400))

    # meta_dict最终要么 dict，要么是None
    meta_dict: dict[str, Any] | None

    # 没传meta就是None
    if meta is None:
        meta_dict = None

    # meta已经是dict就直接用
    elif isinstance(meta, dict):
        meta_dict = meta

    # meta是Mapping就转成dict
    else:
        meta_dict = dict(meta)

    # message如果传了就用传入的；否则用resolve_message得到默认 message
    msg = message if message is not None else resolve_message(c, c)

    # 返回AppError实例
    return AppError(code=c, http_status=st, message=msg, meta=meta_dict)


def raise_err(  # 直接抛出AppError，标注为NoReturn（永不正常返回）
    code: str,
    *,
    http_status: int | None = None,
    message: str | None = None,
    meta: Mapping[str, Any] | None = None,
) -> NoReturn:
    # 抛出由err()构造的AppError
    raise err(code, http_status=http_status, message=message, meta=meta)