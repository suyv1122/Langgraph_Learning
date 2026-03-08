# 创建资产记录: 计算上传摘要(size + sha256 即指纹) -> 标记已上传upload -> 写入storage_key/sha256/size
import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_err
from app.modules.audit.hook import record
from app.modules.kb.consts import ALLOWED_RESOURCE_TYPES, ASSET_STATUS_PENDING, ASSET_STATUS_UPLOADED
from app.modules.kb.models import KBAsset
from app.modules.resources.service import ensure_resource_dir


async def compute_upload_digest(data: bytes) -> tuple[int, str]:
    # 对上传的文件内容计算一个指纹，返回size_bytes字节长度与sha256内容哈希(防止文件被篡改)
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("bad_data")
    h = hashlib.sha256()
    h.update(data)
    return (int(len(data)), h.hexdigest())


async def create_asset( # 建立资产，即插入数据库
    db: AsyncSession,
    *,
    workspace_id: int,
    project_id: int | None,
    created_by: int,
    filename: str,
    mime_type: str | None,
    title: str | None,
    meta: dict[str, Any] | None,
    resource_type: str,
) -> KBAsset:
    rt = str(resource_type or "").strip()
    if rt not in ALLOWED_RESOURCE_TYPES:
        raise_err("kb.asset_bad_resource_type")

    async with db.begin():
        a = KBAsset(
            workspace_id=int(workspace_id),
            project_id=int(project_id) if project_id is not None else None,
            created_by=int(created_by),
            resource_type=str(rt),
            resource_id=None,
            filename=str(filename),
            title=str(title) if title is not None else None,
            mime_type=str(mime_type) if mime_type is not None else None,
            source_type=None,
            storage_key=None,
            size_bytes=None,
            sha256=None,
            status=ASSET_STATUS_PENDING,
            error=None,
            meta=dict(meta) if meta is not None else None,
        )
        db.add(a)   # 相当于INSERT，此时资产在数据库中的条目便建立完成
        await db.flush()
        await db.refresh(a)

        r = await ensure_resource_dir(  # 确认资源条目存在
            db,
            workspace_id=int(workspace_id),
            project_id=int(project_id) if project_id is not None else None,
            resource_type=str(rt),
            ref_id=int(a.id),
            created_by=int(created_by),
        )
        a.resource_id = int(r.id)   # 将存在的资源条目r绑定到asset
        await db.flush()
        await db.refresh(a)

    record(action="kb.asset_create", status="ok", meta={"workspace_id": int(workspace_id), "asset_id": int(a.id), "resource_type": str(rt), "resource_id": int(a.resource_id) if a.resource_id is not None else None})
    return a


async def mark_uploaded(    # 上传完成将asset的状态从pending转为uploaded，并落入上传结果字段(将文件上传完成才能填入的字段填写，像key，大小，sha256等)
    db: AsyncSession,
    *,
    asset_id: int,
    storage_key: str,
    size_bytes: int,
    sha256: str,
) -> KBAsset:
    a = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
    if not a:
        raise_err("kb.asset_not_found")

    async with db.begin():
        a.storage_key = str(storage_key)
        a.size_bytes = int(size_bytes)
        a.sha256 = str(sha256)
        a.status = ASSET_STATUS_UPLOADED
        a.error = None
        await db.flush()
        await db.refresh(a)

    record(action="kb.asset_mark_uploaded", status="ok", meta={"asset_id": int(asset_id), "size_bytes": int(size_bytes)})
    return a