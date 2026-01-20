from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.models.base import Base


class AuditEvent(Base):   # 这个表是审计事件表，用来记录和审计相关的信息
    __tablename__ = "audit_events"
    __table_args__ = (  # 全局性的表格参数，这个表格有哪些索引，主外键等等
        Index("idx_audit_request_id", "request_id"),
        Index("idx_audit_actor_time", "actor_user_id", "created_at"),
        Index("idx_audit_action_time", "action", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_ref_id"),
        {"comment": "Audit trail events"},
    )

    id: 		Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Audit event ID")
    request_id:		Mapped[str | None] = mapped_column(String(128), nullable=True, comment="Correlation request id")

    actor_user_id: 	Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="Actor user_id")
    action: 		Mapped[str] = mapped_column(String(128), nullable=False, comment="Action name")
    scope_key: 		Mapped[str | None] = mapped_column(String(128), nullable=True, comment="Scope key")

    resource_type: 	Mapped[str | None] = mapped_column(String(32), nullable=True, comment="Resource type")
    resource_ref_id: 	Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="Resource ref id")

    status: 		Mapped[str] = mapped_column(String(16), nullable=False, comment="ok/deny/error")
    http_status: 	Mapped[int | None] = mapped_column(Integer, nullable=True, comment="HTTP status")

    ip: 		Mapped[str | None] = mapped_column(String(64), nullable=True, comment="Client IP")
    user_agent: 	Mapped[str | None] = mapped_column(Text, nullable=True, comment="User-Agent")

    meta: 		Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="Extra metadata (json)")

    created_at: 	Mapped[datetime] = mapped_column(
        			DateTime(timezone=True),
        			nullable=False,
        			server_default=func.current_timestamp(),
        			comment="Created time",
    )
