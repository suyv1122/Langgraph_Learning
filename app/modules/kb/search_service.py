# 此条目负责将用户查询query变成一组命中的chunk结果
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastembed import TextEmbedding

from app.core.config import settings
from app.core.errors import raise_err
from app.modules.kb.models import KBChunk
from app.modules.rag.bm25 import BM25Index
from app.modules.rag.dense_qdrant import search_dense
from app.modules.rag.fusion import rrf_fusion


async def _fetch_chunks_for_bm25(   # 辅助类，为BM25模式准备候选文本
    db: AsyncSession,
    *,
    workspace_id: int,
    project_id: int | None,
    limit: int,
) -> list[tuple[int, str]]:
    stmt = select(KBChunk.id, KBChunk.content).where(KBChunk.workspace_id == int(workspace_id)) # 查询步骤
    if project_id is not None:  # 权限检查
        stmt = stmt.where(KBChunk.project_id == int(project_id))
    stmt = stmt.order_by(KBChunk.id.desc()).limit(int(limit))   # 这里的设计限制了limit，即只取一部分查询结果，旧chunk可能被排除在结果之外，有查不到的风险
    rows = (await db.execute(stmt)).all()
    return [(int(i), str(t)) for i, t in rows if t] # 将结果转为(chunk_id, content)形式的列表，并过滤空文本


async def search_kb(    # 返回格式是(chunk_id, score, sources)，例如(789, 0.032, ['bm25', 'dense'])
    db: AsyncSession,
    *,
    qdrant,
    workspace_id: int,
    project_id: int | None,
    query: str,
    mode: str,
    top_k: int,
) -> list[tuple[int, float, list[str]]]:
    q = (query or "").strip()   # 问题去空格保存
    if not q:
        return []

    m = str(mode or "hybrid").strip().lower()   # 模式保存，默认hybrid
    k = max(1, int(top_k))  # 查几条

    # 下面按照(chunk_id, score)格式初始化
    bm25_rank: list[tuple[int, float]] = []
    dense_rank: list[tuple[int, float]] = []

    if m in {"bm25", "hybrid"}: # 若模式是bm25/hybrid则关键词查询
        docs = await _fetch_chunks_for_bm25(db, workspace_id=int(workspace_id), project_id=project_id, limit=int(settings.kb_bm25_max_docs))
        idx = BM25Index(docs=docs)
        hits = idx.search(q, top_k=max(k, 20))
        bm25_rank = [(int(h.doc_id), float(h.score)) for h in hits]

    if m in {"dense", "hybrid"}:    # dense模式则做向量检索
        embedder = TextEmbedding(model_name=str(settings.embedding_model))
        vec = list(embedder.embed([q]))[0]
        qv = list(map(float, list(vec)))
        hits = search_dense(
            qdrant,
            collection=str(settings.qdrant_collection),
            query_vector=qv,
            workspace_id=int(workspace_id),
            project_id=project_id,
            top_k=max(k, 20),
        )
        for h in hits:
            cid = h.payload.get("chunk_id")
            try:
                dense_rank.append((int(cid), float(h.score)))
            except Exception:
                continue

    if m == "bm25":
        return [(cid, sc, ["bm25"]) for cid, sc in bm25_rank[:k]]
    if m == "dense":
        return [(cid, sc, ["dense"]) for cid, sc in dense_rank[:k]]

    fused = rrf_fusion( # rrf公式计算分数
        bm25=bm25_rank,
        dense=dense_rank,
        k=60,
        top_k=k,
    )
    return [(int(x.doc_id), float(x.score), list(x.sources)) for x in fused]