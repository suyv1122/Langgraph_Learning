from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SniffResult:
    mime_type: str | None  # 存放标准的MIME类型
    source_type: str | None  # 音频，视频，图片，文字
    meta: dict[str, Any] | None  # 额外的元数据


def _source_type_from_mime(m: str | None) -> str | None:
    if not m:
        return None
    ml = m.lower()  # 这个参数就是一个标准的MIME字符串
    if ml.startswith("audio/"):
        return "audio"
    if ml.startswith("video/"):
        return "video"
    if ml.startswith("image/"):
        return "image"
    if ml in {"application/pdf"}:
        return "document"
    if ml in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",  # 纯文本，通常是txt
        "text/markdown",  # MD的纯文本，一般就是.md文件
        "text/html",  # html也可以被看作是纯文本，只不过以.html结尾
    }:
        return "document"
    return None


async def sniff(*, filename: str, mime_type_hint: str | None = None) -> SniffResult:
    mt = (mime_type_hint or "").strip() or None
    if mt is None:
        mt, _ = mimetypes.guess_type(str(filename or "").strip())
    st = _source_type_from_mime(mt)
    meta: dict[str, Any] = {"filename": str(filename or "").strip()}
    if mt:
        meta["mime_type"] = mt
    if st:
        meta["source_type"] = st
    return SniffResult(mime_type=mt, source_type=st, meta=meta or None)
