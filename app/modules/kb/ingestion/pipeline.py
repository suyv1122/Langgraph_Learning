from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.kb.consts import (
    ASSET_STATUS_DELETED,
    ASSET_STATUS_FAILED,
    ASSET_STATUS_PROCESSING,
    ASSET_STATUS_READY,
    INDEX_JOB_STATUS_DONE,
    INDEX_JOB_STATUS_FAILED,
    INDEX_JOB_STATUS_RUNNING,
)
from app.modules.kb.ingestion.steps.sniff import sniff
from app.modules.kb.models import KBAsset, KBIndexJob


async def _set_asset_status(
        db: AsyncSession,
        *,
        asset: KBAsset,
        status: str,
        meta_patch: dict[str, Any] | None = None) -> None:
    m = dict(asset.meta or {})  # 文档自身的元数据先取出来
    if meta_patch:  #
        m.update(meta_patch)  # 用一个字典更新另一个字典中的值
    asset.status = str(status)   # asset是一个对象
    asset.meta = m or None
    await db.flush()  # 将上一步已经更新的对象中的信息反馈到数据库表格中
    # 所以此处实际上会执行一个update语句


async def run_ingestion(
    *,
    session_maker: async_sessionmaker[AsyncSession],
    asset_id: int,
) -> None:
    job: KBIndexJob | None = None
    async with session_maker() as db:
        asset = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
        if not asset or asset.status == ASSET_STATUS_DELETED:
            return
        if not asset.storage_key:
            return
        # 上面一段是按照asset_id将这个对象查出来，如果这个文档被标记为删除或者storage_key是none都结束

        async with db.begin():  # 创建一个文档ingest的任务（所谓的创建任务就是向KBIndexJob表中插入一行数据）
            job = KBIndexJob(asset_id=int(asset.id), status=INDEX_JOB_STATUS_RUNNING, started_at=datetime.now(timezone.utc))
            db.add(job)
            await _set_asset_status(db, asset=asset, status=ASSET_STATUS_PROCESSING)

    try:
        sr = await sniff(filename=asset.filename, mime_type_hint=asset.mime_type)
        async with session_maker() as db:
            asset2 = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
            if not asset2 or asset2.status == ASSET_STATUS_DELETED:
                return
            async with db.begin():
                asset2.mime_type = sr.mime_type or asset2.mime_type
                asset2.source_type = sr.source_type or asset2.source_type
                await _set_asset_status(db, asset=asset2, status=ASSET_STATUS_READY, meta_patch=sr.meta or None)
                job2 = (await db.execute(select(KBIndexJob).where(KBIndexJob.id == int(job.id)))).scalar_one_or_none()
                if job2:
                    job2.status = INDEX_JOB_STATUS_DONE
                    job2.finished_at = datetime.now(timezone.utc)
                    await db.flush()
    except Exception as e:
        async with session_maker() as db:
            asset3 = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
            async with db.begin():
                if asset3 and asset3.status != ASSET_STATUS_DELETED:
                    await _set_asset_status(db, asset=asset3, status=ASSET_STATUS_FAILED, meta_patch={"error": str(e)})
                if job is not None:
                    job3 = (await db.execute(select(KBIndexJob).where(KBIndexJob.id == int(job.id)))).scalar_one_or_none()
                    if job3:
                        job3.status = INDEX_JOB_STATUS_FAILED
                        job3.error = str(e)
                        job3.finished_at = datetime.now(timezone.utc)
                        await db.flush()
