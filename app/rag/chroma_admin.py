# 此文件下包含管理员所用，chromadb相关功能的内容，如删除、重建索引、更新可见性等
from __future__ import annotations

from typing import Any
import chromadb
from app.config import settings


def get_collection():
    clint = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return clint.get_or_create_collection(settings.collection_name)


def delete_by_doc_id(doc_id: str) -> int:
    # chromadb特有的api内容，按照doc_id删除其中一个文档
    col = get_collection()  # 此段用于获取向量数据中集合的名字
    try:
        before = col.count()
        col.delete(where={'doc_id': doc_id})
        after = col.count()
        return max(0, int(before - after))
    except Exception:
        got = col.get(where={'doc_id': doc_id})
        ids = got.get('ids') or []
        if ids:
            col.delete(ids=ids)
    return len(ids)


def get_ids_and_metadatas_by_doc_id(doc_id: str) -> tuple[list[str], list[dict[str, Any]]]:
    col = get_collection()
    got = col.get(where={'doc_id': doc_id}, include=['metadatas'])
    ids = got.get('ids') or []
    metas = got.get('metadatas') or []
    return list(ids), list(metas)


def count_by_doc_id(doc_id: str) -> int:
    ids, _ = get_ids_and_metadatas_by_doc_id(doc_id)
    return len(ids)


def update_visibility_by_doc_id(doc_id: str, visibility: str) -> int:
    # 更新文档可见性
    col = get_collection()
    ids, metas = get_ids_and_metadatas_by_doc_id(doc_id)
    if not ids:
        return 0
    new_metas: list[dict[str, Any]] = []
    for m in metas:
        mm = dict(m or {})
        mm['visibility'] = visibility
        new_metas.append(mm)
    col.update(ids=ids, metadatas=new_metas)
    return len(ids)