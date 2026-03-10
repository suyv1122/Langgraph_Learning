# 这个文件用于限制智能体别乱来，这里是一个占位，后期可以无限增长
from __future__ import annotations

from app.core.errors import raise_err
from app.modules.agents.consts import MAX_INPUT_CHARS


def ensure_not_canceled(canceled: bool) -> None:
    if canceled:
        raise_err("agents.run_canceled")


def ensure_input_size(message: str) -> None:
    if len(message or "") > MAX_INPUT_CHARS:
        raise_err("agents.input_too_large")
