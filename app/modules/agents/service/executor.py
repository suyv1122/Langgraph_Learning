# exector是agent用来执行的真正函数，它负责调用run，然后做了一层薄薄的保护
from __future__ import annotations

from typing import Any

from app.modules.agents.engine.state import AgentState
from app.modules.agents.service.dispatcher import resolve_engine
from app.modules.agents.service.guardrails import ensure_not_canceled


async def execute(*, state: AgentState, ctx: dict[str, Any]) -> AgentState:
    ensure_not_canceled(state.canceled)  	# 薄薄的保护在这里：在执行之前确保run任务是存在的
    eng = resolve_engine(ctx.get("engine"))
    return await eng.run(state=state, ctx=ctx)
