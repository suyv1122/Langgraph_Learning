from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ChatReq(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    engine: str | None = None
    workflow: str | None = None
    scope_key: str | None = None
    stream: bool = False


class ChatResp(BaseModel):
    run_id: str
    status: str
    answer: str | None = None
    waiting_approval: bool = False
    approval_id: str | None = None


class RunCreateReq(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    engine: str | None = None
    workflow: str | None = None
    scope_key: str | None = None
    meta: dict[str, Any] | None = None


class RunResp(BaseModel):
    id: str
    status: str
    engine: str
    workflow: str
    scope_key: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RunListResp(BaseModel):  # 上面类的list封装，外面套一个items
    items: list[RunResp]


class RunCancelResp(BaseModel):
    id: str
    canceled: bool