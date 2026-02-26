from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.infra.db.base import Base


class KBAsset(Base):
    __tablename__ = "kb_assets"
    __table_args__ = (
        Index("idx_kb_asset_ws_time", "workspace_id", "created_at"),
        Index("idx_kb_asset_status", "status"),
        Index("idx_kb_asset_creator", "created_by", "created_at"),
        {"comment": "Knowledge base assets (documents/audio/video/images)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id"), nullable=True)

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=True) # 归类，用于区分属于音频/视频/图片/文本

    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=True) # 上传完毕后会计算一个校验信息

    storage_key: Mapped[str] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'pending'"))

    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True) # 此列的类型为json类型，且此列为额外元数据，亦可是暂时没想到的数据

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class KBChunk(Base):
    __tablename__ = "kb_chunks"
    __table_args__ = (
        UniqueConstraint("asset_id", "chunk_index", name="uq_kb_asset_chunk_index"),
        Index("idx_kb_chunk_asset", "asset_id"),
        {"comment": "Extracted chunks for retrieval"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kb_assets.id"), nullable=False)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] =mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    embedding_ref: Mapped[str | None] = mapped_column(String(128), nullable=True) # 此文本块于向量数据库中需要记录的一些信息

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


class KBIndexJob(Base):
    __tablename__ = "kb_index_jobs"
    __table_args__ = (
        Index("idx_kb_index_job_asset", "asset_id"),
        Index("idx_kb_index_job_status", "status", "created_at"),
        {"comment": "Indexing jobs for assets"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kb_assets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'queued'"))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)