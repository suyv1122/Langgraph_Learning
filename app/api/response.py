from __future__ import annotations

from typing import Any

from fastapi import Response

from app.core.http_consts import HDR_CACHE_CONTROL


def no_store(response: Response) -> None:
    # no_store()设置Cache-Control: no-store，直接往相应头里写就行了
    response.headers[HDR_CACHE_CONTROL] = "no-store"


# 组合之前的no_store和ok。这个主要适用于token、me等敏感接口
def ok_no_store(response: Response, data: Any, *, meta: Any | None = None) -> dict:
    no_store(response)
    from app.core.api_response import ok

    no_store(response)
    return ok(data, meta=meta)