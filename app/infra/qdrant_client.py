from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings


def create_qdrant_client() -> QdrantClient:
    api_key = settings.qdrant_api_key.strip() if settings.qdrant_api_key else None
    if api_key:
        return QdrantClient(url=str(settings.qdrant_url), api_key=str(api_key))
    return QdrantClient(url=str(settings.qdrant_url))


def ensure_collection(client: QdrantClient, *, collection: str, vector_size: int) -> None:
    cols = client.get_collections()
    names = {c.name for c in cols.collections} if cols and cols.collections else set()
    if collection in names:
        return
    client.create_collection(
        collection_name=str(collection),
        vectors_config=VectorParams(size=int(vector_size), distance=Distance.COSINE),
    )
