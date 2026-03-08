# 将一个上传的资产文件转为可检索向量
# database取出资产 -> 从存储拉取文件bytes -> 文本抽取 -> 分块 -> 向量化 -> 写入chunks表 -> 写入 Qdrant -> 更新资产/任务状态 -> 审计
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from fastembed import TextEmbedding
from qdrant_client.http.models import PointStruct

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import raise_err
from app.infra.blob_storage.interface import StorageBackend
from app.modules.audit.hook import record
from app.modules.kb.chunking import chunk_text
from app.modules.kb.consts import (
    ASSET_STATUS_FAILED,
    ASSET_STATUS_INDEXING,
    ASSET_STATUS_READY,
    JOB_KIND_INGEST,
    JOB_STATUS_DONE,
    JOB_STATUS_FAILED,
    JOB_STATUS_RUNNING,
)
from app.modules.kb.extractors import extract_text
from app.modules.kb.models import KBAsset, KBChunk, KBIndexJob
from app.modules.rag.dense_qdrant import delete_by_asset, upsert_points


def _point_id(*, asset_id: int, chunk_id: int) -> str:
    # Qdrant的point id 被固定成asset_id : chunk_id 字符串
    return f"{int(asset_id)}:{int(chunk_id)}"


@dataclass(frozen=True)
class IngestResult: # 写入了多少chunk，写入了多少qdrant points，一般数量相等
    chunks: int
    points: int


async def ensure_job_row(db: AsyncSession, *, workspace_id: int, asset_id: int) -> KBIndexJob:
    # 此代码主要做ingest即切分入库，主要讲这个切割任务放入数据库，其余代码不断修改这个切割任务的状态
    # 若这个asset没有INGEST索引任务，就插入一条KBIndexJob，初始为queued
    # 到数据库中查有没有对应的切割任务，如果有直接返回此任务，没有则创建并插入此任务——数据库内容被切割时需要在db中插入一个正在进行此任务的信息
    job = (await db.execute(select(KBIndexJob).where(KBIndexJob.asset_id == int(asset_id), KBIndexJob.job_kind == JOB_KIND_INGEST))).scalar_one_or_none()
    if job:
        return job
    async with db.begin():
        job2 = KBIndexJob(workspace_id=int(workspace_id), asset_id=int(asset_id), job_kind=JOB_KIND_INGEST, status="queued", error=None)
        db.add(job2)
        await db.flush()
        await db.refresh(job2)
        return job2


async def ingest_asset( # 真正对资产做切割
    *,
    db: AsyncSession,
    storage: StorageBackend,
    qdrant,
    asset_id: int,
) -> IngestResult:
    a = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
    if not a:   # 必须存在资产记录，即确认要切割的资产条目存在，资产记录是条目(条目用于描述资产文件本身的状态)
        raise_err("kb.asset_not_found")

    if not a.storage_key:   # 必须已上传到对象存储，即storage_key非空，这是资产文件真正对应的keys
        raise_err("kb.asset_not_uploaded")

    await ensure_job_row(db, workspace_id=int(a.workspace_id), asset_id=int(a.id))  # 确保上一个函数ensure_job_row中的任务存在

    async with db.begin():  # 开启一个事务，将资产状态先变成INDEX，即准备开始切块了
        a.status = ASSET_STATUS_INDEXING
        a.error = None
        await db.flush()

    async with db.begin():  # 开启一个事务，资产状态变为RUNNING，即正在运行
        j = (await db.execute(select(KBIndexJob).where(KBIndexJob.asset_id == int(a.id), KBIndexJob.job_kind == JOB_KIND_INGEST))).scalar_one_or_none()
        if j:
            j.status = JOB_STATUS_RUNNING
            j.error = None
            await db.flush()
        # 这里上文用两次写状态，因为只使用一个事务时如果运行失败，则任务索引也会丢失，即任务从未开始过

    data = await storage.get_bytes(key=str(a.storage_key))  # 拉取文件字节流，得到data，data是一个bytes类型
    text = extract_text(filename=str(a.filename), mime_type=str(a.mime_type) if a.mime_type else None, data=data)   # 将文件二进制字节流变为utf-8规则文本
    if not text:    # 如果为空就开始报错
        async with db.begin():
            a.status = ASSET_STATUS_FAILED
            a.error = "empty_or_unsupported"
            await db.flush()
            j2 = (await db.execute(select(KBIndexJob).where(KBIndexJob.asset_id == int(a.id), KBIndexJob.job_kind == JOB_KIND_INGEST))).scalar_one_or_none()
            if j2:
                j2.status = JOB_STATUS_FAILED
                j2.error = "empty_or_unsupported"
                await db.flush()
        raise_err("kb.ingest_unsupported", meta={"asset_id": int(a.id)})

    chunks = chunk_text(text)   # 文本切块
    if not chunks:
        async with db.begin():
            a.status = ASSET_STATUS_FAILED
            a.error = "no_chunks"
            await db.flush()
            j2 = (await db.execute(select(KBIndexJob).where(KBIndexJob.asset_id == int(a.id), KBIndexJob.job_kind == JOB_KIND_INGEST))).scalar_one_or_none()
            if j2:
                j2.status = JOB_STATUS_FAILED
                j2.error = "no_chunks"
                await db.flush()
        raise_err("kb.ingest_failed", meta={"asset_id": int(a.id), "reason": "no_chunks"})

    embedder = TextEmbedding(model_name=str(settings.embedding_model))  # 利用模型准备好内容嵌入向量数据库
    vectors = list(embedder.embed([c.text for c in chunks]))    # 变向量
    vecs = [list(map(float, v)) for v in vectors]   # 每个向量转为float，qdrant向量数据库要求每个内容均为浮点数
    if len(vecs) != len(chunks):
        raise_err("kb.ingest_failed", meta={"asset_id": int(a.id), "reason": "embed_mismatch"})

    async with db.begin():  # 写入database中的chunk，先删除再插入，此处原文有错误，先删除再插入若插入失败原文也已经删除，则..erm
        await db.execute(delete(KBChunk).where(KBChunk.asset_id == int(a.id)))
        await db.flush()

        db_chunks: list[KBChunk] = []
        for c in chunks:
            db_chunks.append(
                KBChunk(
                    workspace_id=int(a.workspace_id),
                    project_id=int(a.project_id) if a.project_id is not None else None,
                    asset_id=int(a.id),
                    chunk_no=int(c.no),
                    content=str(c.text),
                    meta=None,
                )
            )
        db.add_all(db_chunks)
        await db.flush()
        for cc in db_chunks:
            await db.refresh(cc)

    try:    # 删除Qdrant旧点(旧chunk)，删除失败还不抛出异常，莫名其妙的刻意设计
        delete_by_asset(qdrant, collection=str(settings.qdrant_collection), workspace_id=int(a.workspace_id), asset_id=int(a.id))
    except Exception:
        pass

    points: list[PointStruct] = []  # 构造points并upsert到Qdrant，即转为向量点，上传到qdrant数据库
    for cc, v in zip(db_chunks, vecs):
        payload = {
            "workspace_id": int(a.workspace_id),
            "project_id": int(a.project_id) if a.project_id is not None else 0,
            "asset_id": int(a.id),
            "chunk_id": int(cc.id),
            "resource_type": str(a.resource_type),
        }
        points.append(PointStruct(id=_point_id(asset_id=int(a.id), chunk_id=int(cc.id)), vector=v, payload=payload))

    upsert_points(qdrant, collection=str(settings.qdrant_collection), points=points)    # 将向量真正插入向量数据库

    async with db.begin():  # 更新asset为ready，表示资产已插入向量数据库并可用；更新job为done即工作已完成
        a.status = ASSET_STATUS_READY
        a.error = None
        await db.flush()
        j2 = (await db.execute(select(KBIndexJob).where(KBIndexJob.asset_id == int(a.id), KBIndexJob.job_kind == JOB_KIND_INGEST))).scalar_one_or_none()
        if j2:
            j2.status = JOB_STATUS_DONE
            j2.error = None
            await db.flush()

    record(action="kb.ingest_done", status="ok", meta={"asset_id": int(a.id), "chunks": int(len(db_chunks)), "points": int(len(points))})
    return IngestResult(chunks=int(len(db_chunks)), points=int(len(points)))