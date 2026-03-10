# 当智能体尝试执行一个高风险操作时，必须写入数据库，并等待人工审批；这些操作都放在这个service中
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_err
from app.modules.auth.models import User
from app.modules.agents.approvals.consts import (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_REJECTED,
)
from app.modules.agents.consts import (
    RUN_STATUS_FAILED,
    RUN_STATUS_SUCCEEDED,
    RUN_STATUS_WAITING_APPROVAL,
    STEP_KIND_TOOL,
    STEP_STATUS_FAILED,
    STEP_STATUS_SUCCEEDED,
    STEP_STATUS_WAITING_APPROVAL,
)
from app.modules.agents.models import AgentRun, AgentStep, Approval


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _next_step_ord(db: AsyncSession, run_id: str) -> int:
    # 拿到一个run中下一个step编号，等于是去数据库中查询最大id，然后+1就成了下一个step的id
    current = (
        await db.execute(select(func.max(AgentStep.ord)).where(AgentStep.run_id == str(run_id)))
    ).scalar_one_or_none()
    return int(current or 0) + 1  # 永远都是现有step+1，如果没有那就从1开始


async def create_approval_for_tool(  # 用某个工具干些什么事情，这个事情又需要被人类确认，就放入数据库去等待人类批准
    *,
    request: Request,
    db: AsyncSession,
    user: User,
    run_id: str,
    tool_name: str,
    payload: dict,
    scope_key: str | None,
    reason: str | None,
) -> dict:
    run = (await db.execute(select(AgentRun).where(AgentRun.id == str(run_id)))).scalar_one_or_none()
    if not run:
        raise_err("agents.run_not_found")

    step = AgentStep(
        id=uuid.uuid4().hex,
        run_id=str(run_id),
        ord=await _next_step_ord(db, str(run_id)),
        kind=STEP_KIND_TOOL,
        name=str(tool_name),
        status=STEP_STATUS_WAITING_APPROVAL,
        scope_key=str(scope_key) if scope_key else None,
        input=dict(payload or {}),
        output=None,
        error=None,
        started_at=_now(),
        finished_at=None,
    )
    appr = Approval(
        id=uuid.uuid4().hex,
        status=APPROVAL_STATUS_PENDING,
        run_id=str(run_id),
        step_id=str(step.id),
        tool_name=str(tool_name),
        scope_key=str(scope_key) if scope_key else None,
        payload=dict(payload or {}),
        reason=str(reason) if reason else None,
        workspace_id=getattr(request.state, "workspace_id", None),
        requested_by=int(user.id),
        decided_by=None,
        decided_at=None,
        decision_reason=None,
    )
    run.status = RUN_STATUS_WAITING_APPROVAL
    run.output = {
        "approval_id": str(appr.id),
        "waiting_approval": True,
        "tool_name": str(tool_name),
    }
    db.add(step)
    db.add(appr)
    await db.commit()
    await db.refresh(appr)
    return {"approval_id": str(appr.id), "run_id": str(run_id), "status": APPROVAL_STATUS_PENDING}


async def decide_approval(
    *,
    request: Request,
    db: AsyncSession,
    actor: User,
    approval_id: str,
    approve: bool,
    reason: str | None = None,
) -> dict:
    appr = (await db.execute(select(Approval).where(Approval.id == str(approval_id)))).scalar_one_or_none()
    if not appr:
        raise_err("agents.approval_not_found")

    run = (await db.execute(select(AgentRun).where(AgentRun.id == appr.run_id))).scalar_one_or_none()
    step = (await db.execute(select(AgentStep).where(AgentStep.id == appr.step_id))).scalar_one_or_none()
    if not run or not step:
        raise_err("agents.approval_targets_missing")

    appr.status = APPROVAL_STATUS_APPROVED if approve else APPROVAL_STATUS_REJECTED
    appr.decided_by = int(actor.id)
    appr.decided_at = _now()
    appr.decision_reason = str(reason) if reason else None

    if approve:
        requester = (await db.execute(select(User).where(User.id == appr.requested_by))).scalar_one_or_none()
        if requester is None:
            requester = actor

        from app.modules.agents.tools.router import dispatch_tool

        out = await dispatch_tool(  # 人类已经同意，所以需要调用工具来完成后续操作
            request=request,
            db=db,
            user=requester,
            run_id=run.id,
            step_id=step.id,
            tool_name=str(appr.tool_name),
            scope_key=appr.scope_key,
            payload=dict(appr.payload or {}),
            skip_approval=True,
        )
        step.status = STEP_STATUS_SUCCEEDED
        step.output = dict(out or {})
        step.error = None
        step.finished_at = _now()
        run.status = RUN_STATUS_SUCCEEDED
        run.error = None
        run.output = {"approval_id": appr.id, "approved": True, "tool_output": dict(out or {})}
    else:
        step.status = STEP_STATUS_FAILED
        step.error = {"code": "approval.rejected", "reason": reason}
        step.finished_at = _now()
        run.status = RUN_STATUS_FAILED
        run.error = {"code": "approval.rejected", "reason": reason}
        run.output = {"approval_id": appr.id, "approved": False}

    await db.commit()
    return {"approval_id": appr.id, "approved": bool(approve), "run_id": run.id}