from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.middleware.real_ip import get_real_ip
from app.core.http_consts import HDR_REQUEST_ID, HDR_RESPONSE_TIME_MS, STATE_REQUEST_ID
from app.core.request_context import set_client_ip, set_request_id, set_user_agent, set_user_id
from app.modules.audit.hook import flush_audit, init_audit

_MAX_RID_LEN = 128
_RE_SAFE_RID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _sanitize_request_id(v: str | None) -> str:
    if not v:
        return uuid.uuid4().hex
    v = v.strip()
    if not v or len(v) > _MAX_RID_LEN:
        return uuid.uuid4().hex
    if not _RE_SAFE_RID.match(v):
        return uuid.uuid4().hex
    return v


async def _finalize_request(request: Request, response) -> None:
    try:
        await flush_audit(request, response)
        # 审计、日志等出错，不能影响正常代码执行
    finally:
        set_request_id(None)
        set_user_id(None)
        set_client_ip(None)
        set_user_agent(None)


class RequestContextMiddleware(BaseHTTPMiddleware):
    # 这段代码就是向请求头里面放好相关的请求头
    async def dispatch(self, request: Request, call_next):
        rid = _sanitize_request_id(request.headers.get(HDR_REQUEST_ID))
        setattr(request.state, STATE_REQUEST_ID, rid)

        set_request_id(rid)
        set_user_id(None)
        set_client_ip(get_real_ip(request))
        set_user_agent(request.headers.get("User-Agent"))

        init_audit()  # 审计勾子里面的初始化审计对象

        start = time.perf_counter()
        resp = await call_next(request)
        cost_ms = int((time.perf_counter() - start) * 1000)
        # 调用某个请求所耗费的时间/单位是毫秒

        resp.headers[HDR_REQUEST_ID] = rid
        resp.headers[HDR_RESPONSE_TIME_MS] = str(cost_ms)

        if resp.background is None:
            resp.background = BackgroundTask(_finalize_request, request, resp)
        else:
            prev = resp.background

            async def _chain() -> None:
                await prev()
                await _finalize_request(request, resp)

            resp.background = BackgroundTask(_chain)

        return resp