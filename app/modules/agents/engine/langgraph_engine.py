from __future__ import annotations

from app.modules.agents.engine.state import AgentState
from app.modules.agents.workflows.registry import get_workflow


class LangGraphEngine:
    async def run(self, *, state: AgentState, ctx: dict) -> AgentState:
        wf = get_workflow(state.workflow)
        return await wf.run(state=state, ctx=ctx)
