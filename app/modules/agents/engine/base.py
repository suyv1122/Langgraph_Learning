from __future__ import annotations

from typing import Protocol

from app.modules.agents.engine.state import AgentState


class AgentEngine(Protocol):  # Python的鸭子类型，类似于Java中的接口，C++中的虚函数
    # 这个方法run就是一个agent引擎要做的事情，所以这里留空，即具体干什么由子类补充
    async def run(self, *, state: AgentState, ctx: dict) -> AgentState: ...