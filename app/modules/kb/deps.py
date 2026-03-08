from __future__ import annotations

from fastapi import Depends, Request

from app.core.errors import raise_err
from app.infra.blob_storage.interface import StorageBackend


def get_workspace_id_or_400(request: Request) -> int:   # 尽可能确认工作区id，否则丢400
    wid = getattr(request.state, "workspace_id", None)
    try:
        wid_i = int(wid) if wid is not None else 0
    except Exception:
        wid_i = 0
    if wid_i <= 0:
        raise_err("error.http", http_status=400, message="workspace_id_required")
    return int(wid_i)


def get_storage(request: Request) -> StorageBackend:    # 文件到底存在何处
    st = getattr(request.app.state, "storage", None)
    if st is None:
        raise_err("error.internal", meta={"where": "get_storage", "reason": "storage_not_initialized"})
    return st