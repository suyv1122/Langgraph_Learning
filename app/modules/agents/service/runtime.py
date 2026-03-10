from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.auth.models import User
from app.modules.agents.consts import (
    RUN_STATUS_FAILED,
    RUN_STATUS_QUEUED,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCEEDED,
)
from app.modules.agents.engine.state import AgentState
from app.modules.agents.models import AgentRun
from app.modules.agents.service.executor import execute
from app.modules.agents.service.guardrails import ensure_input_size
from app.modules.agents.service.planner import plan


async def start_run(
    *,
    request: Request,
    db: AsyncSession,
    user: User,
    message: str,
    engine: str,
    workflow: str,
    scope_key: str | None,
    meta: dict[str, Any] | None = None,
) -> AgentRun:
    ensure_input_size(message)
    wf = plan(workflow=workflow, message=message).workflow
    run = AgentRun(
        id=uuid.uuid4().hex,
        user_id=int(user.id),
        workspace_id=getattr(request.state, "workspace_id", None),
        engine=str(engine),
        workflow=str(wf),
        scope_key=str(scope_key) if scope_key else None,
        status=RUN_STATUS_QUEUED,
        input={"message": str(message), "meta": dict(meta or {})},
        output=None,
        error=None,
        canceled=0,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    run.status = RUN_STATUS_RUNNING
    await db.commit()

    state = AgentState(
        run_id=str(run.id),
        user_id=int(user.id),
        message=str(message),
        engine=str(engine),
        workflow=str(wf),
        scope_key=str(scope_key) if scope_key else None,
        data={"meta": dict(meta or {})},
    )

    try:
        final_state = await execute(
            state=state,
            ctx={"engine": engine, "request": request, "db": db, "user": user},
        )
        run.status = "waiting_approval" if final_state.waiting_approval else RUN_STATUS_SUCCEEDED
        run.output = {
            "answer": final_state.answer,
            "approval_id": final_state.approval_id,
            "steps": final_state.steps,
            "data": final_state.data,
        }
        run.error = final_state.error
    except AppError as e:
        run.status = RUN_STATUS_FAILED
        run.error = {
            "type": e.__class__.__name__,
            "code": str(e.code),
            "message": str(e.message or e.code),
            "http_status": int(e.http_status),
            "meta": dict(e.meta or {}),
        }
    except Exception as e:
        run.status = RUN_STATUS_FAILED
        run.error = {"type": e.__class__.__name__, "message": str(e)}

    await db.commit()
    await db.refresh(run)
    return run