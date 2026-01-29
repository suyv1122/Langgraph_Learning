from __future__ import annotations

from fastapi import Request

def get_real_ip(request: Request) -> str | None:
    xff = request.headers.get("X-Forwarded-For")
    # X-Forwarded-For是我经过的所有的ip的列表，用逗号分开
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]  # 最左侧的ip就是你的初始ip地址

    xri = request.headers.get("X-Real-IP")  # X-Real-IP真实IP
    if xri and xri.strip():
        return xri.strip()

    if request.client:
        return request.client.host

    return None