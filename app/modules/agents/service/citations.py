# 把智能体返回的引用/citation数据，清洗成统一格式
# 非常重要，只有这个类清洗后才能返回合规的数据，不至于让下游代码崩溃
from __future__ import annotations

from typing import Any


def normalize_citations(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in list(items or []):
        if not isinstance(item, dict):
            continue
        src = {str(k): v for k, v in item.items() if v is not None}
        if src:
            out.append(src)
    return out
