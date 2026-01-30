# 1.4
from __future__ import annotations

from typing import Any
from fastapi import Response 	 # FastAPI/Starlette的响应对象，用于设置响应头
from pydantic import BaseModel
from app.core.api_schemas import Meta
from app.core.http_consts import HDR_CACHE_CONTROL  # 1.1里面的常量


# 这里返回dict而不是直接返回BaseModel，是为了让FastAPI用response_model时自行序列化
def ok(data: Any, meta: dict[str, Any] | Meta | None = None) -> dict:
    if meta is None:
        return {"data": data}

    if isinstance(meta, Meta):
        return {"data": data, "meta": meta.model_dump()}  # 使用model_dump()转成dict

    if isinstance(meta, BaseModel):
        return {"data": data, "meta": meta.model_dump()}

    # 如果都不是，把meta当成映射对象转dict
    return {"data": data, "meta": dict(meta)}