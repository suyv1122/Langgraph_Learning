from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.audio.asr import ASRSegment


@dataclass
class Chunk:
    start_ms: int
    end_ms: int
    text: str


def merge_by_max_duration(
        segs: List[ASRSegment],
        max_ms: int = 25_000,   # 25秒
        min_ms: int = 6_000,    # 太短会被合并
) -> List[Chunk]:
    """将ASR segments合并成更适合检索的chunk"""
    chunks: List[Chunk] = []
    cur_start = None
    cur_end = None
    buf: list[str] = []

    def flush():
        nonlocal cur_start, cur_end, buf
        if cur_start is None or cur_end is None:
            return
        text = ' '.join(buf).strip()
        if text:
            chunks.append(Chunk(start_ms=cur_start, end_ms=cur_end, text=text))
        cur_start, cur_end, buf = None, None, []

    for s in segs:
        s_start = int(s.start_s * 1000)
        s_end = int(s.end_s * 1000)
        if cur_start is None:
            cur_start, cur_end = s_start, s_end
            buf = [s.text]
            continue

        new_end = max(cur_end, s_end)
        if (new_end - cur_start) <= max_ms:
            cur_end = new_end
            buf.append(s.text)
        else:
            # 若当前音频太短，则拼接后再切分，出于避免碎片的目的
            if (cur_end - cur_start) <= min_ms:
                cur_end = new_end
                buf.append(s.text)
            flush()
            cur_start, cur_end = s_start, s_end
            buf = [s.text]

    flush()
    return chunks