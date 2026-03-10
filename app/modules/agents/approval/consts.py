# 审批状态常量，审批智能体能不能帮我们做这个事情。和具体请假审批不是一回事
from __future__ import annotations

APPROVAL_STATUS_PENDING = "pending"    # 待审批
APPROVAL_STATUS_APPROVED = "approved"  # 已批准
APPROVAL_STATUS_REJECTED = "rejected"  # 已拒绝