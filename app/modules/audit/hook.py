from __future__ import annotations

from typing import Any, Awaitable, Callable, cast

_record_impl: Callable[..., Any] | None = None
_init_impl: Callable[[], Any] | None = None
_flush_impl: Callable[[Any, Any], Awaitable[Any]] | None = None

_resolved_record: bool = False
_resolved_mw: bool = False


def _resolve_record() -> Callable[..., Any] | None:
    global _record_impl, _resolved_record
    if _resolved_record:
        return _record_impl
    _resolved_record = True
    try:
        from app.modules.audit.service import record as impl
        _record_impl = cast(Callable[..., Any], impl)
    except Exception:
        _record_impl = None
    return _record_impl

def record(
    *,
    action: str,
    status: str = "ok",
    http_status: int | None = None,
    scope_key: str | None = None,
    resource_type: str | None = None,
    resource_ref_id: int | None = None,
    actor_user_id: int | None = None,
    meta: Any | None = None,
    error_code: str | None = None,
) -> None:
    impl = _resolve_record()
    if impl is None:
        return
    impl(
        action=action,
        status=status,
        http_status=http_status,
        scope_key=scope_key,
        resource_type=resource_type,
        resource_ref_id=resource_ref_id,
        actor_user_id=actor_user_id,
        meta=meta,
        error_code=error_code,
    )


def _resolve_middleware() -> tuple[Callable[[], Any], Callable[[Any, Any], Awaitable[Any]]]:
    global _init_impl, _flush_impl, _resolved_mw
    if _resolved_mw and _init_impl is not None and _flush_impl is not None:
        return _init_impl, _flush_impl

    _resolved_mw = True
    try:
        from app.modules.audit.middleware import flush_audit as _flush
        from app.modules.audit.middleware import init_audit as _init

        _init_impl = cast(Callable[[], Any], _init)
        _flush_impl = cast(Callable[[Any, Any], Awaitable[Any]], _flush)
    except Exception:

        def _noop_init() -> None:
            return None

        async def _noop_flush(_request: Any, _response: Any) -> None:
            return None

        _init_impl = _noop_init
        _flush_impl = _noop_flush

    return _init_impl, _flush_impl


def init_audit() -> None:
    init_fn, _ = _resolve_middleware()
    init_fn()


async def flush_audit(request: Any, response: Any) -> None:
    _, flush_fn = _resolve_middleware()
    await flush_fn(request, response)

if __name__=='__main__':
    print(init_audit())