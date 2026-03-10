from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    run_id: str
    user_id: int
    message: str
    engine: str
    workflow: str
    scope_key: str | None = None
    answer: str | None = None
    canceled: bool = False
    waiting_approval: bool = False
    approval_id: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
