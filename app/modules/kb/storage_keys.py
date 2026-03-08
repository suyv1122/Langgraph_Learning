# 存储的资源(无论云端/本地)都应有独属于自己的keys，不能撞名
# 即将文件名校验，替换掉不支持的字符后，确保名称独立性
from __future__ import annotations

import re

_RE_SAFE = re.compile(r"[^A-Za-z0-9._-]+")  # 文件名只允许正则表达式限制的内容

def _safe_name(s: str) -> str:  # 将文件名清洗成安全可用的名称并限制长度，不符合正则表达式的元素会替换成下划线
    s = (s or "").strip()
    if not s:
        return "file"
    s = _RE_SAFE.sub("_", s)
    return s[:200] if len(s) > 200 else s


def asset_original_key(*, workspace_id: int, asset_id: int, filename: str) -> str:
    # 为资产原始文件生成统一的储存路径key
    fn = _safe_name(filename)
    # 注意返回值，不要project id 是合理且正确的
    return f"ws/{int(workspace_id)}/assets/{int(asset_id)}/original/{fn}"