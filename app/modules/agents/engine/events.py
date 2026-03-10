from __future__ import annotations

from typing import Any


def event(name: str, **payload: Any) -> dict[str, Any]:
    return {"event": str(name), "payload": payload}  # 引擎的事件信息的标准返回格式