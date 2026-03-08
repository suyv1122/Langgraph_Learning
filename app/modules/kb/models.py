from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.infra.db.base import Base


class KBAsset(Base):    # 资产表，每个资产就是一个文件，此表记录了这些文件的基本信息
    __tablename__ = "kb_assets"
    __table_args__ = (
        Index("idx_kb_asset_ws", "workspace_id", "created_at"),
        Index("idx_kb_asset_proj", "project_id", "created_at"),
        Index("idx_kb_asset_status", "status", "created_at"),
        {"comment": "Knowledge base assets (docs/audio/video/images)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("projects.id"), nullable=True)

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("resources.id"), nullable=True)

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'pending'"))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)    # 元数据，以json类型储存

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class KBChunk(Base):    # 每一个资产都要被切块，此处是每个资产切割后的表格信息
    # 设置有复合主键，用于确保唯一性
    __tablename__ = "kb_chunks"
    __table_args__ = (
        UniqueConstraint("asset_id", "chunk_no", name="uq_kb_chunk_asset_no"),
        Index("idx_kb_chunk_asset", "asset_id"),
        Index("idx_kb_chunk_ws", "workspace_id", "asset_id"),
        {"comment": "Chunk registry for assets"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("projects.id"), nullable=True)
    asset_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kb_assets.id"), nullable=False)

    chunk_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


class KBIndexJob(Base): # 每一个资产对应的处置任务信息相关表格
    __tablename__ = "kb_index_jobs"
    __table_args__ = (
        UniqueConstraint("asset_id", "job_kind", name="uq_kb_job_asset_kind"),
        Index("idx_kb_job_ws", "workspace_id", "created_at"),
        Index("idx_kb_job_status", "status", "created_at"),
        {"comment": "Index jobs per asset"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kb_assets.id"), nullable=False)

    job_kind: Mapped[str] = mapped_column(String(32), nullable=False)   # 要对资产如何处置？
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'queued'"))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )