from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateAssetReq(BaseModel):    # 建立一个对资产的请求需要什么内容
    filename: str = Field(min_length=1, max_length=512)
    title: str | None = Field(default=None, max_length=512)
    mime_type: str | None = Field(default=None, max_length=128)
    project_id: int | None = None
    resource_type: str = Field(min_length=1, max_length=32)
    meta: dict[str, Any] | None = None


class AssetResp(BaseModel): # 对资产请求的响应会返回的内容
    id: int
    workspace_id: int
    project_id: int | None
    created_by: int
    resource_type: str
    resource_id: int | None
    filename: str
    title: str | None
    mime_type: str | None
    source_type: str | None
    size_bytes: int | None
    sha256: str | None
    storage_key: str | None
    status: str
    error: str | None
    meta: dict[str, Any] | None
    created_at: str
    updated_at: str


class UploadResp(BaseModel):    # 定义资产上传完成后的返回数据结构
    asset_id: int
    storage_key: str
    size_bytes: int
    sha256: str


class EnqueueIngestResp(BaseModel): # 定义资产入队执行ingest任务后的返回数据结构
    ok: bool = True
    task_name: str = "kb.ingest_asset"
    asset_id: int