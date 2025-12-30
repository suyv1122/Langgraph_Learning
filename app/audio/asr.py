from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from faster_whisper import WhisperModel


@dataclass # 数据类
class ASRSegment:
    start_s: float # 开始时间
    end_s: float # 结束时间
    text: str # 转成文字后的文本


class ASR:
    def __init__(self, model_name: str = 'base', device: str = 'cpu', compute_type: str = 'int8'):
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcribe(self, wav_path: str, language: Optional[str] = None) -> tuple[List[ASRSegment], Optional[str]]:
        segments_iter, info = self.model.transcribe(
            wav_path,
            language=language,
            vad_filter=False, # 筛选无声部分音频并切除，早期版本先行关闭
        )
        segs: List[ASRSegment] = []
        for s in segments_iter:
            txt = (s.text or '').strip()
            if not txt:
                continue
            segs.append(ASRSegment(start_s=float(s.start), end_s=float(s.end), text=txt))

        lang = getattr(info, 'language', None)
        return segs, lang

if __name__ == "__main__":
    segs, lang = ASR.transcribe('../data/test.wav')
    for s in segs:
        print(s)
    print(lang)