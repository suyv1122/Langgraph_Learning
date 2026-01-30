from __future__ import annotations

import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.request_context import set_workspace_id

_HDR_WORKSPACE_ID = "X-Workspace-Id"

_RE_WS_PATH = re.compile(r"/workspaces/(\d+)(?:/|$)")
_RE_WS_PATH2 = re.compile(r"/workspace/(\d+)(?:/|$)")


def _to_int(v: object) -> int | None:
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        try:
            v = v.decode("utf-8")
        except Exception:
            return None
    try:
        return int(str(v).strip())
    except Exception:
        return None


def _extract_from_path(path: str) -> int | None:
    m = _RE_WS_PATH.search(path or "")
    if m:
        try:
            v = int(m.group(1))
            return v if v > 0 else None
        except Exception:
            return None
    m = _RE_WS_PATH2.search(path or "")
    if m:
        try:
            v = int(m.group(1))
            return v if v > 0 else None
        except Exception:
            return None
    return None


def _extract_workspace_id(request: Request) -> int | None:
    wid = _to_int(request.headers.get(_HDR_WORKSPACE_ID))
    if wid and wid > 0:
        return int(wid)

    wid = _to_int(request.query_params.get("workspace_id"))
    if wid and wid > 0:
        return int(wid)

    wid = _extract_from_path(request.url.path)
    if wid and wid > 0:
        return int(wid)

    return None


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        wid = _extract_workspace_id(request)
        setattr(request.state, "workspace_id", wid)
        set_workspace_id(wid)
        return await call_next(request)