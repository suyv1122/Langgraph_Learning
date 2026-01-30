# NOTE: 这是一个 S3 协议兼容的存储后端（AWS S3 / 阿里云 OSS / 腾讯云 COS / MinIO 等）。
# NOTE: 真实项目里 endpoint/bucket/ak/sk 来自配置（.env / secrets），不要硬编码到仓库。
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Mapping

import boto3
from botocore.exceptions import ClientError

from dataclasses import dataclass

from app.infra.blob_storage.interface import StorageBackend, StoredObject

@dataclass(frozen=True)
class S3CompatStorage(StorageBackend):
    endpoint_url: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    region: str | None = None

    def _make_client(self):
        # Create a fresh client (thread-safe for our use with asyncio.to_thread).
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )

    def _make_stored_object(self, **kwargs: Any) -> StoredObject:
        """Create StoredObject without depending on its exact field set.

        Different training projects may evolve the `StoredObject` shape. We filter kwargs
        by the constructor signature so this backend keeps working as fields change.
        """
        try:
            sig = inspect.signature(StoredObject)  # type: ignore[arg-type]
            allowed = set(sig.parameters.keys())
            filtered = {k: v for k, v in kwargs.items() if k in allowed}
            return StoredObject(**filtered)  # type: ignore[call-arg]
        except Exception:
            # Last resort: try to call with only the key if possible.
            if "key" in kwargs:
                return StoredObject(key=kwargs["key"])  # type: ignore[call-arg]
            raise

    async def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> StoredObject:
        def _do_put() -> Mapping[str, Any]:
            client = self._make_client()
            extra: dict[str, Any] = {}
            if content_type:
                extra["ContentType"] = content_type
            resp = client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)
            # boto3 returns headers like ETag in response dict.
            return resp

        resp = await asyncio.to_thread(_do_put)
        etag = resp.get("ETag")
        return self._make_stored_object(
            key=key,
            bucket=self.bucket,
            size=len(data),
            content_type=content_type,
            etag=etag,
        )

    async def get_bytes(self, *, key: str) -> bytes:
        def _do_get() -> bytes:
            client = self._make_client()
            resp = client.get_object(Bucket=self.bucket, Key=key)
            body = resp["Body"].read()
            # StreamingBody.read() returns bytes
            return body

        return await asyncio.to_thread(_do_get)

    async def exists(self, *, key: str) -> bool:
        def _do_head() -> bool:
            client = self._make_client()
            try:
                client.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError as e:
                code = str(e.response.get("Error", {}).get("Code", ""))
                # Common not-found codes across providers
                if code in {"404", "NoSuchKey", "NotFound"}:
                    return False
                raise

        return await asyncio.to_thread(_do_head)

    async def delete(self, *, key: str) -> None:
        def _do_delete() -> None:
            client = self._make_client()
            try:
                client.delete_object(Bucket=self.bucket, Key=key)
            except ClientError as e:
                # Deleting a missing object is typically safe to treat as success.
                code = str(e.response.get("Error", {}).get("Code", ""))
                if code in {"404", "NoSuchKey", "NotFound"}:
                    return
                raise

        await asyncio.to_thread(_do_delete)

# TODO: 注意此处
# 留一个“对象存储”接口层，底层可以换 AWS S3、阿里 OSS、腾讯 COS、MinIO 之类，只要它们支持 S3 协议（或有 S3 兼容网关）就行。
# 做了这些事：
#  用 boto3（同步库）+ asyncio.to_thread 把阻塞 I/O 丢到线程里跑，保证你 FastAPI/async 不会被卡死
#  实现了 put_bytes / get_bytes / exists / delete 四个核心操作
#  对 StoredObject 做了字段自适应：我不知道你们项目里 StoredObject 到底有哪些字段，所以我运行时检查构造函数签名，只传它能接受的字段。以后你们 StoredObject 加字段、删字段都不容易把这里弄爆
