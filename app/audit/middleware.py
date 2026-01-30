# 中间键
from __future__ import annotations

import logging

from fastapi import Request

from app.audit.context import clear_audit_context, init_audit_context, pop_audit_events
from app.audit.models import AuditEvent
from app.core.request_context import get_client_ip, get_request_id, get_user_agent, get_user_id

logger = logging.getLogger(__name__)


def init_audit() -> None:  # 初始化审计上下文的入口函数
    init_audit_context()


def _classify(status_code: int) -> str:  # 根据HTTP状态码把结果分类为ok/deny/error
    if status_code in {401, 403, 429}:
        return "deny"
    if status_code >= 400:
        # 其他4xx/5xx归为error（客户端错误或服务端错误）
        return "error"
    return "ok"


async def flush_audit(request: Request, response) -> None:
    # 把本次请求缓冲区里的审计事件写入数据库
    try:
        status_code = int(getattr(response, "status_code", 500) or 500)
        events = pop_audit_events()

        if not events and status_code >= 400:
            # 如果没有显式记录事件，但响应是错误状态，则补一条“http.error”事件
            rid = get_request_id()
            uid = get_user_id()
            events = [  # 构造一个包含单条事件的列表
                {
                    "request_id": rid,
                    "actor_user_id": uid,
                    "action": "http.error",
                    "scope_key": None,
                    "resource_type": None,
                    "resource_ref_id": None,
                    "status": _classify(status_code),
                    "http_status": status_code,
                    "ip": str(get_client_ip()) if get_client_ip() else None,
                    "user_agent": str(get_user_agent()) if get_user_agent() else None,
                    "meta": {"method": request.method, "path": request.url.path},
                }
            ]

        if not events:  # 如果仍然没有任何事件直接返回
            return

        session_maker = request.app.state.db_session_maker  # 从应用状态取出数据库session工厂
        async with session_maker() as db:
            async with db.begin_nested():
                for e in events:
                    if e.get("http_status") is None:
                        e["http_status"] = status_code  # 设置字段为响应状态码
                    db.add(AuditEvent(**e))
    except Exception:
        logger.exception("audit_flush_failed")
    finally:
        clear_audit_context()  # 清空ContextVar，避免污染后续请求