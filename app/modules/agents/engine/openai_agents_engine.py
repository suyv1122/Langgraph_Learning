from __future__ import annotations

from app.modules.agents.engine.state import AgentState
from app.modules.agents.tools.adapter_openai_agents import run_with_openai_agents


class OpenAIAgentsEngine:
    async def run(self, *, state: AgentState, ctx: dict) -> AgentState:
        return await run_with_openai_agents(state=state, ctx=ctx)
