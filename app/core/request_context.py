# 1.7
from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)
_user_agent: ContextVar[str | None] = ContextVar("user_agent", default=None)
_workspace_id: ContextVar[int | None] = ContextVar("workspace_id", default=None)


def set_request_id(v: str | None) -> None:
    _request_id.set(v)


def get_request_id() -> str | None:
    return _request_id.get()


def set_user_id(v: int | None) -> None:
    _user_id.set(v)


def get_user_id() -> int | None:
    return _user_id.get()


def set_client_ip(v: str | None) -> None:
    _client_ip.set(v)


def get_client_ip() -> str | None:
    return _client_ip.get()


def set_user_agent(v: str | None) -> None:
    _user_agent.set(v)


def get_user_agent() -> str | None:
    return _user_agent.get()


def set_workspace_id(v: int | None) -> None:
    _workspace_id.set(v)


def get_workspace_id() -> int | None:
    return _workspace_id.get()