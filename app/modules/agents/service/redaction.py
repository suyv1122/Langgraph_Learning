# 调用core里面的脱敏完成和智能体相关的脱敏操作
# 这个文件就是简单包装，不是特别必须
from __future__ import annotations

from typing import Any

from app.core.redaction import redact_obj


def redact(value: Any) -> Any:
    return redact_obj(value)
