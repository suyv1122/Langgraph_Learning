# 向量数据库做检索
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, PayloadSchemaType, PointStruct, VectorParams

@dataclass(frozen=True)
class DenseHit:             # 定义单条向量检索命中结果的结构
    point_id: str           # 命中的 向量点 id(向量点: 存进向量库里的一条记录)
    score: float
    payload: dict[str, Any] # 载荷，命中点附带的业务字段数据，因为非精确检索，防止近似内容


def ws_filter(*, workspace_id: int, project_id: int | None = None, asset_id: int | None = None) -> Filter:
    # 生成按workspace_id, project_id, asset_id 过路的Qdrant的查询条件
    must: list[Any] = [ # 生成条件列表，这里命名must是因为这些条件需要同时满足
        FieldCondition(key="workspace_id", match=MatchValue(value=int(workspace_id))),
    ]
    if project_id is not None:
        must.append(FieldCondition(key="project_id", match=MatchValue(value=int(project_id))))
    if asset_id is not None:
        must.append(FieldCondition(key="asset_id", match=MatchValue(value=int(asset_id))))
    return Filter(must=must)


def ensure_payload_schema(client: QdrantClient, *, collection: str) -> None:
    # 为Qdrant集合设置载荷(payload)字段的类型schema
    # 或者说 为每个小chunk设计的元数据格式，即每个chunk的元数据载荷的内容规定
    client.set_payload_schema(
        collection_name=str(collection),
        payload_schema={
            "workspace_id": PayloadSchemaType.INTEGER,
            "project_id": PayloadSchemaType.INTEGER,
            "asset_id": PayloadSchemaType.INTEGER,
            "chunk_id": PayloadSchemaType.INTEGER,
            "resource_type": PayloadSchemaType.KEYWORD,
        },
    )


def upsert_points(  # 将一批 向量点(chunk) 写入或更新到指定的Qdrant集合中
    client: QdrantClient,
    *,
    collection: str,
    points: list[PointStruct],   # 要写入或更新的向量点列表，PointStruct就是一堆chunk
) -> None:
    if not points:
        return
    client.upsert(collection_name=str(collection), points=points)


def delete_by_asset(client: QdrantClient, *, collection: str, workspace_id: int, asset_id: int) -> None:
    # 删除指定工作区下某个资产对应的所有向量点(删除指定工作区下某资产的所有chunk)
    flt = ws_filter(workspace_id=int(workspace_id), asset_id=int(asset_id))
    client.delete(collection_name=str(collection), points_selector=flt)


def search_dense(   # 在指定工作区和范围项目内执行向量检索并返回结果列表
    client: QdrantClient,
    *,
    collection: str,
    query_vector: list[float],
    workspace_id: int,
    project_id: int | None,
    top_k: int,
) -> list[DenseHit]:
    flt = ws_filter(workspace_id=int(workspace_id), project_id=int(project_id) if project_id is not None else None)
    res = client.search(
        collection_name=str(collection),
        query_vector=list(query_vector),
        query_filter=flt,
        with_payload=True,
        limit=max(1, int(top_k)),
    )
    out: list[DenseHit] = []
    for p in res:
        payload = dict(p.payload or {})
        out.append(DenseHit(point_id=str(p.id), score=float(p.score or 0.0), payload=payload))
    return out