from __future__ import annotations

from pydantic import BaseModel, Field


class ApprovalDecision(BaseModel):  # 审批决定
    approve: bool  # 同意与否
    reason: str | None = Field(default=None, max_length=1000)  # 理由


class ApprovalItem(BaseModel):  # 一条审批记录
    id: str
    run_id: str  # 关联的智能体运行ID
    step_id: str  # 关联的步骤ID
    tool_name: str  # 申请执行的工具名，比如发邮件，写代码等等
    status: str  # 审批状态，之前的常量
    scope_key: str | None = None
    reason: str | None = None  # 发起人的理由，比如我不想吃饭
    decision_reason: str | None = None  # 拒绝理由，比如你必须吃饭
    requested_by: int  # 谁提出的申请
    decided_by: int | None = None  # 谁决定的


class ApprovalListResp(BaseModel):  # 把上一个类包起来，加一个前缀item
    items: list[ApprovalItem]

