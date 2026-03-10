# 新增智能体工具审批策略；对高风险的角色授权/撤销操作强制进入approval流程
from __future__ import annotations

from typing import Any


def evaluate_tool_access(*, tool_name: str, approval_policy: str | None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})

    if approval_policy == "role_grant":  # 授予智能体相关角色
        return {"requires_approval": True, "reason": "role grant is a privileged mutation"}
    if approval_policy == "role_revoke":  # 撤销智能体相关角色
        return {"requires_approval": True, "reason": "role revoke is a privileged mutation"}

    return {"requires_approval": False, "reason": None}
