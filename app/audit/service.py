from __future__ import annotations

import dataclasses
from typing import Any

from pydantic import BaseModel

from app.audit.context import add_audit_event
from app.core.redaction import redact_obj
from app.core.request_context import get_client_ip, get_request_id, get_user_agent, get_user_id


def _to_obj(v: Any) -> Any:	# 把各种对象转换为可序列化的基础结构
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, BaseModel):
        return v.model_dump()
    if dataclasses.is_dataclass(v):
        return dataclasses.asdict(v)
    if isinstance(v, dict):
        return {str(k): _to_obj(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_to_obj(x) for x in v]
    return str(v)


def _normalize_meta(meta: Any | None) -> dict[str, Any] | None:
# 把meta归一化为dict或None
    if meta is None:
        return None
    if isinstance(meta, dict):
        return {str(k): _to_obj(v) for k, v in meta.items()}
    return {"value": _to_obj(meta)}	# 非dict的meta用 {"value": ...} 包一层


def _std_meta(	# 标准化meta，同时注入error_code，并脱敏
    *,
    meta: Any | None,
    error_code: str | None,
) -> dict[str, Any] | None:
    m = _normalize_meta(meta)
    if error_code is None:
        return redact_obj(m)
    if m is None:
        m2: dict[str, Any] = {"error_code": str(error_code)}
    else:
        m2 = dict(m)
        m2.setdefault("error_code", str(error_code))
    return redact_obj(m2)


def record(	# 记录一条审计事件到当前请求的缓冲区————不直接写DB
    *,
    action: str,	# 动作名
    status: str = "ok",
    http_status: int | None = None,
    scope_key: str | None = None,
    resource_type: str | None = None,
    resource_ref_id: int | None = None,
    actor_user_id: int | None = None,
    meta: Any | None = None,
    error_code: str | None = None,
) -> None:
    evt = {	# 构造审计事件dict
        "request_id": get_request_id(),
        "actor_user_id": actor_user_id if actor_user_id is not None else get_user_id(),
        "action": str(action),
        "scope_key": str(scope_key) if scope_key is not None else None,
        "resource_type": str(resource_type) if resource_type is not None else None,
        "resource_ref_id": int(resource_ref_id) if resource_ref_id is not None else None,
        "status": str(status),
        "http_status": int(http_status) if http_status is not None else None,
        "ip": str(get_client_ip()) if get_client_ip() else None,
        "user_agent": str(get_user_agent()) if get_user_agent() else None,
        "meta": _std_meta(meta=meta, error_code=error_code),
    }
    add_audit_event(evt)