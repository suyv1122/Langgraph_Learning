from __future__ import annotations

from app.modules.agents.engine.state import AgentState


def dumps_state(state: AgentState) -> dict:  # 对象变JSON/str（序列化）
    return {
        "run_id": state.run_id,
        "user_id": state.user_id,
        "message": state.message,
        "engine": state.engine,
        "workflow": state.workflow,
        "scope_key": state.scope_key,
        "answer": state.answer,
        "canceled": state.canceled,
        "waiting_approval": state.waiting_approval,
        "approval_id": state.approval_id,
        "steps": state.steps,
        "data": state.data,
        "error": state.error,
    }


def loads_state(obj: dict) -> AgentState:  # 反序列化，即dict/str变回对象
    return AgentState(
        run_id=str(obj["run_id"]),
        user_id=int(obj["user_id"]),
        message=str(obj["message"]),
        engine=str(obj["engine"]),
        workflow=str(obj["workflow"]),
        scope_key=obj.get("scope_key"),
        answer=obj.get("answer"),
        canceled=bool(obj.get("canceled")),
        waiting_approval=bool(obj.get("waiting_approval")),
        approval_id=obj.get("approval_id"),
        steps=list(obj.get("steps") or []),
        data=dict(obj.get("data") or {}),
        error=obj.get("error"),
    )
