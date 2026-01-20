from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_audit_events: ContextVar[list[dict[str, Any]] | None] = ContextVar("audit_events", default=None)

def init_audit_context() -> None:	# 初始化刚才的变量，用作审计缓冲区（收集审计事件）
    _audit_events.set([])   # _audit_events变量是一个ContextVar类型，其包含一个set方法，用于往其中加东西

def clear_audit_context() -> None: 	# 清理审计上下文
    _audit_events.set(None) # 清理，实际上也是set方法放东西，但放的是None，便等于删除效果

def add_audit_event(evt: dict[str, Any]) -> None:
    buf = _audit_events.get()	# 取出当前上下文的事件列表
    if buf is None:
        return
    buf.append(evt)

def pop_audit_events() -> list[dict[str, Any]]:	# 弹出并清空当前缓冲区中的事件
    buf = _audit_events.get()

    if not buf:
        return []

    out = list(buf)
    buf.clear()

    return out