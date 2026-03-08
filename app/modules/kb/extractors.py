# 此文件负责识别并读取word, pdf, txt和md文件类型，并将其转换成str类型
from __future__ import annotations

import io

from docx import Document
from pypdf import PdfReader


def _as_text_utf8(data: bytes) -> str:  # 二进制字符串转为字符串，很多文本是二进制字节流
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""


def extract_text(*, filename: str, mime_type: str | None, data: bytes) -> str:
    # mimetype https标准协议中的一部分，里面会说明网站资源都有什么类型，
    # 其内容形状类似于 'application/pdf', 'application/msword' 等
    fn = (filename or "").lower()
    mt = (mime_type or "").lower().strip()

    if fn.endswith(".pdf") or mt == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for p in reader.pages:
            try:
                t = p.extract_text() or ""
            except Exception:
                t = ""
            if t:
                parts.append(t)
        return "\n\n".join(parts).strip()

    if fn.endswith(".docx") or mt in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(parts).strip()

    if fn.endswith(".txt") or fn.endswith(".md") or mt.startswith("text/"):
        return _as_text_utf8(data).strip()

    return ""