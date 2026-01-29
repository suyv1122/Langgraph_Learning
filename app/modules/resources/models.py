from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infra.db.base import Base


class Workspace(Base):  # 工作区，可以包含多个工程，一张表
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("name", name="uq_workspace_name"), {"comment": "Workspace/Org container"})

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Workspace ID")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Workspace name (unique)")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Workspace description")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), comment="Created time"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="Updated time",
    )


class Project(Base):    # 工程，可同时属于多个工作区；多个工程之间可互相协作
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_ws_project_name"),
        Index("idx_project_ws", "workspace_id"),
        {"comment": "Project container under workspace"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Project ID")
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id"), nullable=False, comment="FK -> workspaces.id"
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Project name (unique within workspace)")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Project description")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), comment="Created time"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="Updated time",
    )


class Resource(Base):  # 统一资源目录是把业务资源映射为可授权对象，我们这里是workspace/project/resource三层结构
    __tablename__ = "resources"
    __table_args__ = (
        Index(
            "uq_resource_ws_proj_type_ref",
            "workspace_id",
            "project_id",
            "resource_type",
            "ref_id",
            unique=True,
            postgresql_where=text("project_id IS NOT NULL"),
        ),
        Index(
            "uq_resource_ws_type_ref_no_proj",
            "workspace_id",
            "resource_type",
            "ref_id",
            unique=True,
            postgresql_where=text("project_id IS NULL"),
        ),
        Index("idx_type_ref", "resource_type", "ref_id"),
        {"comment": "Unified resource directory for authorization"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Resource row ID (internal)")
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id"), nullable=False, comment="Owning workspace id"
    )
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=True, comment="Owning project id (nullable)"
    )
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="doc/audio/image/ticket/... (extensible)")
    ref_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Business table PK this resource refers to")
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, comment="Creator user_id")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), comment="Created time"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="Updated time",
    )