from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BlobObject:
    key: str
    size_bytes: int


class StorageBackend(Protocol):
    async def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> BlobObject: ...
    async def get_bytes(self, *, key: str) -> bytes: ...
    async def delete(self, *, key: str) -> None: ...
    async def exists(self, *, key: str) -> bool: ...