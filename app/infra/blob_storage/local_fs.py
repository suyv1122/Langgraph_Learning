from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

import aiofiles

from app.infra.blob_storage.interface import StorageBackend, StoredObject


def _safe_key(key: str) -> str:
    k = str(key or "").strip()
    if not k or k.startswith("/") or ".." in k:
        raise ValueError("bad_storage_key")
    return k.replace("\\", "/")


def _join(root: str, key: str) -> str:
    key = _safe_key(key)
    p = os.path.abspath(os.path.join(root, key))
    r = os.path.abspath(root)
    if not p.startswith(r + os.sep) and p != r:
        raise ValueError("bad_storage_key")
    return p


@dataclass(frozen=True)
class LocalFSStorage(StorageBackend):
    root_dir: str

    def __post_init__(self) -> None:
        os.makedirs(self.root_dir, exist_ok=True)

    async def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> StoredObject:
        p = _join(self.root_dir, key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        async with aiofiles.open(p, "wb") as f:
            await f.write(data)
        etag = hashlib.sha256(data).hexdigest()
        return StoredObject(key=key, size=len(data), content_type=content_type, etag=etag)

    async def get_bytes(self, *, key: str) -> bytes:
        p = _join(self.root_dir, key)
        async with aiofiles.open(p, "rb") as f:
            return await f.read()

    async def exists(self, *, key: str) -> bool:
        p = _join(self.root_dir, key)
        return os.path.exists(p)

    async def delete(self, *, key: str) -> None:
        p = _join(self.root_dir, key)
        try:
            os.remove(p)
        except FileNotFoundError:
            return