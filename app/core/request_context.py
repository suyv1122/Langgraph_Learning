from __future__ import annotations

from contextvars import ContextVar  # ContextVar用于在async并发环境下保存每个请求独立的上下文变量

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
# _request_id保存当前请求的request_id

_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
# _user_id保存当前请求关联的user_id，未登录时None

_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)
# _client_ip保存解析出的客户端IP

_user_agent: ContextVar[str | None] = ContextVar("user_agent", default=None)
# _user_agent保存User-Agent头

# 下面是一些get和set方法
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
