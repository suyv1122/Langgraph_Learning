from __future__ import annotations

from app.core.errors import raise_err
from app.modules.agents.consts import DEFAULT_MAX_STEPS, DEFAULT_MAX_TOOL_CALLS


def ensure_step_limit(step_count: int, max_steps: int = DEFAULT_MAX_STEPS) -> None:
    # 此处限制智能体一个run中的step不能超过预定的阈值
    if int(step_count) >= int(max_steps):
        raise_err("agents.step_limit_exceeded")


def ensure_tool_limit(tool_count: int, max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS) -> None:
    # 此处限制智能体一个run中的调用的工具数量不能超过预定的阈值
    if int(tool_count) >= int(max_tool_calls):
        raise_err("agents.tool_limit_exceeded")