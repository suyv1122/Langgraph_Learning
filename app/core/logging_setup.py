# 1.9
from __future__ import annotations

import dataclasses
import json
import logging
from datetime import date, datetime
from logging.config import dictConfig
from typing import Any

from pydantic import BaseModel

from app.core.redaction import redact_obj
from app.core.request_context import get_request_id, get_user_id


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = getattr(record, "request_id", None)
        uid = getattr(record, "user_id", None)

        if not rid:
            rid2 = get_request_id()
            if rid2:
                setattr(record, "request_id", rid2)

        if uid is None:
            uid2 = get_user_id()
            if uid2 is not None:
                setattr(record, "user_id", uid2)

        return True


_MAX_JSON_DEPTH = 6
_MAX_STR_LEN = 8192


def _safe_str(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    if len(s) > _MAX_STR_LEN:
        return s[:_MAX_STR_LEN] + "...(truncated)"
    return s


def _bytes_to_text(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return _safe_str(repr(b))


def _to_jsonable(obj: Any, *, _depth: int = 0) -> Any:
    if _depth > _MAX_JSON_DEPTH:
        return "...(max_depth)" # 递归终止条件，超过最大深度返回占位符，防止过深递归

    if obj is None:
        return None
    if isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return _safe_str(obj)
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return _bytes_to_text(bytes(obj))

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, BaseModel):
        try:
            return _to_jsonable(obj.model_dump(), _depth=_depth + 1)
        except (TypeError, ValueError):
            return _safe_str(str(obj))

    if dataclasses.is_dataclass(obj):
        try:
            return _to_jsonable(dataclasses.asdict(obj), _depth=_depth + 1)
        except (TypeError, ValueError):
            return _safe_str(str(obj))

    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            kk = _safe_str(k)
            out[kk] = _to_jsonable(v, _depth=_depth + 1)
        return out

    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x, _depth=_depth + 1) for x in obj]
    if isinstance(obj, set):
        return [_to_jsonable(x, _depth=_depth + 1) for x in obj]

    if isinstance(obj, BaseException):
        return {"type": obj.__class__.__name__, "message": _safe_str(str(obj))}

    return _safe_str(str(obj))


class JsonFormatter(logging.Formatter): # 对日志格式化
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),  # 日志级别，info,error等
            "logger": record.name,              # logger的名字
            "message": record.getMessage(),     # 日志内容
        }   # 日志载荷，日志的大体模样

        rid = getattr(record, "request_id", None) or get_request_id()
        uid = getattr(record, "user_id", None)
        if uid is None:
            uid = get_user_id()

        if rid:
            payload["request_id"] = rid # 向payload中添加一个键值对
        if uid is not None:
            payload["user_id"] = uid

        if record.exc_info: # 若有异常堆栈信息，将格式化后的异常文本放进载荷
            payload["exc_info"] = self.formatException(record.exc_info)

        for k, v in record.__dict__.items():    # python自带的record带有过多信息，格式化过滤掉冗余内容
            if k in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                continue    # 这些内容包括内置字段与噪音字段
            if k in payload:
                continue    # 若payload已有同名键便跳过，防止覆盖
            payload[k] = v  # 若以上条件均不满足，正常写入载荷

        safe_payload = _to_jsonable(payload)    # 将payload转换为json(格式化)
        safe_payload = redact_obj(safe_payload) # 将payload脱敏

        try:
            return json.dumps(safe_payload, ensure_ascii=False) # 调用标准库，使payload真正转为json
                                                                # 参数表示允许输出中文等非ASCII自负
        except (TypeError, ValueError, OverflowError):  # OverflowError 栈溢出，常见于自我递归次数过多
            fallback = {
                "level": record.levelname.lower(),
                "logger": record.name,
                "message": _safe_str(record.getMessage()),
                "request_id": rid,
                "user_id": uid,
                "format_error": True,
            }   # 若序列化失败，以最小可控字段都低，并标记format_error，一个保底日志
            return json.dumps(redact_obj(_to_jsonable(fallback)), ensure_ascii=False)   # 保底信息也需脱敏


def setup_logging(*, level: str = "INFO") -> None:  # 记录日志之前需要先设置记录那些内容，这是python自带的诸多限制
    level = (level or "INFO").upper()   # 通常均为大写，约定

    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context": {"()": "app.core.logging_setup.ContextFilter"},
        },
        "formatters": {
            "json": {"()": "app.core.logging_setup.JsonFormatter"},
        },
        "handlers": {   # 日志处理器
            "stdout": { # 标准输出，默认格式，几乎无法调试
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["context"],
                "level": level,
            }
        },
        "root": {"handlers": ["stdout"], "level": level},   # 除非特别要求的日志，负责均以root内配置输出日志
        "loggers": {
            "uvicorn": {"level": level},
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"level": level, "propagate": False, "handlers": ["stdout"]},
            "access": {"level": level, "propagate": False, "handlers": ["stdout"]},
        },
    }
    # - version: 配置版本固定写1
    # - disable_existing_loggers: 是否禁用已有的logger
    # -

    dictConfig(cfg)