from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import json
import re


class InternalMethod(BaseModel):
    @staticmethod
    def _safe_json_load(s: str) -> Dict[str, Any]:
        """将str格式的json变为一个python中的字典"""
        if not s:
            return {}
        s = s.strip()
        if s.startswith('```'):
            s = s.strip('`')
            if s.lower().startswith('json'):
                s = s[4:].strip()
        try:
            return json.loads(s)  # json.loads(data) 用于将一个符合json格式的str变为dict
        except Exception:
            return {}

    @staticmethod
    def _safe_iso(s: Any) -> str | None:
        """检查一个str表示的时间是否符合iso格式，如果符合则转为datetime并返回"""
        if not s or not isinstance(s, str):
            print('日期格式转换失败，检查其是否符合iso格式')
            return None
        s = s.strip()
        try:
            datetime.fromisoformat(s)
            return s
        except Exception:
            return None

    @staticmethod
    def _extract_leave_id(text: str) -> str | None:
        if not text:
            return None
        # re.search，按照正则表达式限制搜索字段内容
        # m本身是个compile类型，m.group(0)才是需要的字符串
        m = re.search(r"\bLV-[0-9a-fA-F]{6,12}\b", text)
        return m.group(0) if m else None

