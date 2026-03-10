# 将答案做进一步的规范，这里是简单的留一个壳，后续也可以无限补充内容
from __future__ import annotations


def format_answer(answer: str | None) -> str:
    return (answer or "").strip()  # 这里只是简单的去空格，后续可以大量补充