from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.api_schemas import ErrorInfo, ErrorResponse
from app.core.errors import AppError, resolve_message
from app.core.http_consts import HDR_REQUEST_ID, STATE_REQUEST_ID
from app.modules.audit.hook import record

logger = logging.getLogger(__name__)

# 错误处理，以及自定义四个错误类型，会被install函数加入fastapi包中
def _get_request_id(request: Request) -> str:
    rid = getattr(request.state, STATE_REQUEST_ID, None)
    if isinstance(rid, str) and rid:
        return rid
    rid = request.headers.get(HDR_REQUEST_ID)
    if rid:
        return rid
    return uuid.uuid4().hex


def _build_error(
        *,
        code: str,
        message: Any,
        request_id: str,
        meta: dict[str, Any] | None = None,
) -> dict:
    payload = ErrorResponse(error=ErrorInfo(code=code, message=message, request_id=request_id, meta=meta))
    return payload.model_dump()


def install_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        rid = _get_request_id(request)
        st = int(exc.http_status)
        record(
            action="http.app_error",
            status="error" if st >= 500 else "deny" if st in {401, 403, 429} else "error",
            http_status=st,
            meta={"path": request.url.path, "method": request.method},
            error_code=str(exc.code),
        )
        return JSONResponse(
            status_code=st,
            content=_build_error(code=str(exc.code), message=exc.message, request_id=rid, meta=exc.meta),
            headers={HDR_REQUEST_ID: rid},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        rid = _get_request_id(request)
        record(
            action="http.validation_failed",
            status="deny",
            http_status=422,
            meta={"path": request.url.path, "method": request.method, "errors": exc.errors()},
            error_code="error.validation_failed",
        )
        return JSONResponse(
            status_code=422,
            content=_build_error(
                code="error.validation_failed",
                message=resolve_message("error.validation_failed"),
                request_id=rid,
                meta={"errors": exc.errors()},
            ),
            headers={HDR_REQUEST_ID: rid},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        rid = _get_request_id(request)
        detail = exc.detail

        code = "error.http"
        msg = resolve_message(code, "http_error")
        meta: dict[str, Any] | None = None

        if isinstance(detail, dict) and "code" in detail:
            code = str(detail.get("code"))
            msg = detail.get("message", resolve_message(code, code))
            meta_val = detail.get("meta")
            if meta_val is None:
                meta = None
            elif isinstance(meta_val, dict):
                meta = meta_val
            else:
                meta = {"value": meta_val}
        elif isinstance(detail, str) and detail.strip():
            code = detail.strip()
            msg = resolve_message(code, code)
            meta = None

        record(
            action="http.http_exception",
            status="deny" if int(exc.status_code) in {401, 403, 429} else "error",
            http_status=int(exc.status_code),
            meta={"path": request.url.path, "method": request.method, "detail_meta": meta},
            error_code=str(code),
        )

        return JSONResponse(
            status_code=int(exc.status_code),
            content=_build_error(code=code, message=msg, request_id=rid, meta=meta),
            headers={HDR_REQUEST_ID: rid},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        rid = _get_request_id(request)
        logger.error(
            "unhandled_error",
            extra={"request_id": rid},
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        record(
            action="http.unhandled_error",
            status="error",
            http_status=500,
            meta={"path": request.url.path, "method": request.method, "exc_type": exc.__class__.__name__},
            error_code="error.internal",
        )
        return JSONResponse(
            status_code=500,
            content=_build_error(code="error.internal", message=resolve_message("error.internal"), request_id=rid),
            headers={HDR_REQUEST_ID: rid},
        )