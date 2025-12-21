# 此处模型来自数据库内查出的内容，经由用户需求筛选组成
# 具体哪些内容被需要，会根据后续代码随时添加或删除
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KBDocListItem(BaseModel):
    doc_id: str
    original_filename: str
    stored_path: str
    visibility: str
    uploader_user_id: Optional[int] = None
    uploader_username: Optional[str] = None
    chunk_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KBDocDetail(KBDocListItem):
    chroma_chunk_count: int = 0


class KBDocVisibilityUpdateReq(BaseModel):
    visibility: str = Field(..., min_length=1)


class KBDocReembedResp(BaseModel):
    doc_id: str
    deleted_chunks: int
    new_chunks: int
    visibility: str