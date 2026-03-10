# 根据用户传入的engine名字决定这次Agent Run到底用哪个执行引擎
from __future__ import annotations

from app.modules.agents.engine.langgraph_engine import LangGraphEngine
from app.modules.agents.engine.openai_agents_engine import OpenAIAgentsEngine


def resolve_engine(name: str | None):
    n = (name or "langgraph").strip().lower()
    if n in {"langgraph", "default"}:
        return LangGraphEngine()
    if n in {"openai", "openai_agents", "openai-agents"}:
        return OpenAIAgentsEngine()
    return LangGraphEngine()
