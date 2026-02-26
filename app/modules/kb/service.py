from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_err
from app.modules.kb.consts import (
    ASSET_STATUS_DELETED,
    ASSET_STATUS_PENDING,
    ASSET_STATUS_UPLOADED,
)
from app.modules.kb.ingestion.utils import sha256_bytes
from app.modules.kb.models import KBAsset


async def create_asset(
    db: AsyncSession,
    *,
    workspace_id: int,
    project_id: int | None,
    created_by: int,
    filename: str,
    mime_type: str | None = None,
    title: str | None = None,
    meta: dict[str, Any] | None = None,
) -> KBAsset:
    a = KBAsset(
        workspace_id=int(workspace_id),
        project_id=int(project_id) if project_id is not None else None,
        created_by=int(created_by),
        filename=str(filename),
        title=str(title) if title is not None else None,
        mime_type=str(mime_type) if mime_type is not None else None,
        status=ASSET_STATUS_PENDING,
        meta=dict(meta) if meta is not None else None,
    )
    async with db.begin():
        db.add(a)
        await db.flush()
        await db.refresh(a)
    return a


async def mark_uploaded(
    db: AsyncSession,
    *,
    asset_id: int,
    storage_key: str,
    size_bytes: int,
    sha256: str,
) -> KBAsset:
    a = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
    if not a or a.status == ASSET_STATUS_DELETED:
        raise_err("error.http", http_status=404, message="asset_not_found")
    async with db.begin():
        a.storage_key = str(storage_key)
        a.size_bytes = int(size_bytes)
        a.sha256 = str(sha256)
        a.status = ASSET_STATUS_UPLOADED
        await db.flush()
        await db.refresh(a)
    return a


async def soft_delete_asset(db: AsyncSession, *, asset_id: int) -> None:
    a = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
    if not a or a.status == ASSET_STATUS_DELETED:
        return
    async with db.begin():
        a.status = ASSET_STATUS_DELETED
        await db.flush()


async def compute_upload_digest(data: bytes) -> tuple[int, str]:
    return len(data), sha256_bytes(data)