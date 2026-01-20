from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

from elasticsearch import Elasticsearch, helpers

from app.config import settings


AUDIO_INDEX = getattr(settings, "es_audio_index", "audio_segments_v1")
# ES中的索引名字，读取es_audio_index的值，没有就取audio_segments_v1

@lru_cache(maxsize=1)
def es_client() -> Elasticsearch:
    return Elasticsearch(
        hosts=[settings.es_url],
        request_timeout=30,
        retry_on_timeout=True,
        max_retries=3,
    )


def ensure_audio_index() -> None:
    es = es_client()
    if es.indices.exists(index=AUDIO_INDEX):
        return

    mappings = {
        "properties": {
            "audio_id": {"type": "keyword"},
            "segment_id": {"type": "keyword"},
            "segment_idx": {"type": "integer"},
            "start_ms": {"type": "integer"},
            "end_ms": {"type": "integer"},
            "visibility": {"type": "keyword"},  # 精确用来检索的，不分词
            "text": {
                "type": "text",  # 人类读，分词
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
        }
    }

    settings_body = {
        "index": {
            "number_of_shards": 1,  # 整个索引只有一个主分片
            "number_of_replicas": 0,  # 不设置副本
            "refresh_interval": "1s", # 定期刷新索引使新写入的数据可以被搜索到
        }
    }

    es.indices.create(index=AUDIO_INDEX, mappings=mappings, settings=settings_body)


def reset_audio_index() -> None:
    es = es_client()
    if es.indices.exists(index=AUDIO_INDEX):
        es.indices.delete(index=AUDIO_INDEX)
    ensure_audio_index()


def upsert_audio_segments(*, audio_id: str, rows: list[dict[str, Any]]) -> int:
    """把某个音频文件的多个segments批量写入或更新到es中"""
    ensure_audio_index()
    es = es_client()

    actions = []
    for r in rows:
        seg_id = str(r.get("segment_id") or "").strip()
        seg_idx = int(r.get("segment_idx"))
        actions.append(
            {
                "_op_type": "index",
                "_index": AUDIO_INDEX,
                "_id": f"{audio_id}:{seg_idx}",
                "_source": {
                    "audio_id": audio_id,
                    "segment_id": seg_id or f"{audio_id}:{seg_idx}",
                    "segment_idx": seg_idx,
                    "start_ms": int(r.get("start_ms") or 0),
                    "end_ms": int(r.get("end_ms") or 0),
                    "text": str(r.get("text") or ""),
                    "visibility": str(r.get("visibility") or "public"),
                },
            }
        )

    if not actions:
        return 0

    ok, _ = helpers.bulk(es, actions, refresh=True)
    return int(ok)


def delete_by_audio_id(audio_id: str) -> int:
    ensure_audio_index()
    es = es_client()
    resp = es.delete_by_query(
        index=AUDIO_INDEX,
        query={"term": {"audio_id": audio_id}},  # term查询是精确匹配，不分词
        refresh=True,  # 操作完成后立即刷新索引
        conflicts="proceed",  # 冲突时继续执行，不报错
    )
    return int(resp.get("deleted") or 0)


def delete_many_audio_ids(audio_ids: Iterable[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for aid in audio_ids:
        aid = (aid or "").strip()
        if not aid:
            continue
        try:
            out[aid] = int(delete_by_audio_id(aid))
        except Exception:
            out[aid] = 0
    return out


def update_visibility_by_audio_id(audio_id: str, visibility: str) -> int:
    ensure_audio_index()
    es = es_client()
    resp = es.update_by_query(
        index=AUDIO_INDEX,
        query={"term": {"audio_id": audio_id}},
        script={
            "source": "ctx._source.visibility = params.v",
            "lang": "painless",  # Painless是es官方默认的脚本语言
            "params": {"v": visibility},
        },
        refresh=True,
        conflicts="proceed",
    )
    return int(resp.get("updated") or 0)


@dataclass(frozen=True)  # 初始化后不能再修改它的属性
class ESKeywordHit:  # 这里主要存放es命中结果
    audio_id: str
    segment_id: str
    segment_idx: int
    start_ms: int
    end_ms: int
    text: str
    score: float

def keyword_search(*, q: str, k: int, allowed_visibilities: list[str]) -> list[ESKeywordHit]:
    ensure_audio_index()
    es = es_client()

    k = max(1, min(int(k), 200))
    allowed = [v for v in (allowed_visibilities or []) if v]

    body = {
        "size": k,
        "query": {
            "bool": {
                "must": [  # WHERE条件
                    {
                        "simple_query_string": {  # 全文搜索匹配, 类似于mysql的MATCH(text) AGAINST()
                            "query": q,
                            "fields": ["text"],
                            "default_operator": "and",  # 默认操作用AND visibility IN (...)
                        }
                    }
                ],
                "filter": [{"terms": {"visibility": allowed}}] if allowed else [],
            }
        },
    }  # 类似于sql SELECT * FROM audio_segments WHERE MATCH(text) AGAINST (:q IN BOOLEAN MODE)AND visibility IN (:allowed) LIMIT :k;

    resp = es.search(index=AUDIO_INDEX, **body)
    hits = resp.get("hits", {}).get("hits", []) or []

    out: list[ESKeywordHit] = []
    for h in hits:
        src = h.get("_source") or {}
        out.append(
            ESKeywordHit(
                audio_id=str(src.get("audio_id") or ""),
                segment_id=str(src.get("segment_id") or ""),
                segment_idx=int(src.get("segment_idx") or 0),
                start_ms=int(src.get("start_ms") or 0),
                end_ms=int(src.get("end_ms") or 0),
                text=str(src.get("text") or ""),
                score=float(h.get("_score") or 0.0),
            )
        )
    return out