from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineConfig:  # 某个引擎的配置信息
    name: str   # 引擎的名字
    max_steps: int = 40   # 做一个run里面最多的steps
    max_tool_calls: int = 40  # 一个run调用工具的数量