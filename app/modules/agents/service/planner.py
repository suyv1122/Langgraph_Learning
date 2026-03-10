# 当不知道走哪个工作流的时候帮agent进行选择或提示(_ACTION_HINTS)
# 这里也基本就是留了一个壳，后续可以添加很多复杂规则
from __future__ import annotations

from dataclasses import dataclass

from app.modules.agents.consts import DEFAULT_WORKFLOW

_ACTION_HINTS = (
    "grant role",
    "revoke role",
    "授权",
    "回收角色",
    "撤销角色",
    "权限",
)


@dataclass(frozen=True)
class Plan:
    workflow: str


def infer_workflow_from_message(message: str | None) -> str:
    text = (message or "").strip()
    lower = text.lower()
    if any(hint in lower or hint in text for hint in _ACTION_HINTS):
        return "action_runner"
    return DEFAULT_WORKFLOW


def plan(*, workflow: str | None, message: str | None = None) -> Plan:
    explicit = (workflow or "").strip()
    if explicit:
        return Plan(workflow=explicit)
    return Plan(workflow=infer_workflow_from_message(message))