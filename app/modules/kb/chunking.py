# 文件切割
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True) # frozen 最好别加, python会于后台加内容，某些情况下会导致出错
class Chunk:    # 表示一个文本分块对象，包含分块编号(no, number)与分块内容(text)
    no: int
    text: str


def chunk_text(text: str) -> list[Chunk]:   # 按配置的长度与重叠参数将文本切分成多个Chunk
    s = (text or "").strip()
    if not s:
        return []
    max_chars = int(settings.kb_chunk_max_chars)    # 每个文本分块对象的长度
    overlap = int(settings.kb_chunk_overlap_chars)  # 相邻文本分块对象内容的重叠长度
    if max_chars <= 100:
        max_chars = 100
    if overlap < 0:
        overlap = 0
    if overlap >= max_chars:
        overlap = max_chars // 5

    out: list[Chunk] = []   # 储存着切分后的分块
    i = 0
    n = 0
    L = len(s)
    while i < L:
        j = min(L, i + max_chars)
        part = s[i:j].strip()
        if part:
            out.append(Chunk(no=n, text=part))
            n += 1
        if j >= L:
            break
        i = max(0, j - overlap)
    return out