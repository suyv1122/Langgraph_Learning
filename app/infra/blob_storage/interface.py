from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    size: int
    content_type: str | None = None
    etag: str | None = None


class StorageBackend(Protocol):
    async def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> StoredObject: ...
    async def get_bytes(self, *, key: str) -> bytes: ...
    async def exists(self, *, key: str) -> bool: ...
    async def delete(self, *, key: str) -> None: ...