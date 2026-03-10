from __future__ import annotations

from fastapi import Request

from app.modules.authz.deps import any_permission_required, permission_required
from app.modules.authz.scope_keys import scope_global, scope_workspace


def agent_scope(request: Request) -> str:  # 早晚会重写，应该是简单占位
    # 轻薄封装或者是临时写一下
    wid = getattr(request.state, "workspace_id", None)
    try:
        wid_i = int(wid) if wid is not None else 0
    except Exception:
        wid_i = 0

    if wid_i > 0:
        return scope_workspace(wid_i)

    return scope_global()


AgentUser = permission_required("agent.use", scope_builder=agent_scope)

AgentApprover = any_permission_required(
    "agent.approval.review",
    "workspace.manage",
    scope_builder=agent_scope,
)