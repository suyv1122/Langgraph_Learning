from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security_defaults import (
    DEFAULT_HSTS_MAX_AGE,
    DEFAULT_PERMISSIONS_POLICY,
    DEFAULT_REFERRER_POLICY,
    DEFAULT_X_FRAME_OPTIONS,
)

# 这个类主要就是向resp中塞入大量的响应头为后续的安全使用
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        hsts: bool = True,
        hsts_max_age: int = DEFAULT_HSTS_MAX_AGE,
        include_subdomains: bool = True,
        preload: bool = False,
        x_content_type_options: bool = True,
        x_frame_options: str = DEFAULT_X_FRAME_OPTIONS,
        referrer_policy: str = DEFAULT_REFERRER_POLICY,
        permissions_policy: str = DEFAULT_PERMISSIONS_POLICY,
        content_security_policy: str | None = None,
    ):
        super().__init__(app)  # 调用父类构造器
        self.hsts = hsts
        self.hsts_max_age = hsts_max_age
        self.include_subdomains = include_subdomains
        self.preload = preload
        self.x_content_type_options = x_content_type_options
        self.x_frame_options = x_frame_options
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy
        self.csp = content_security_policy

    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request) # 调用请求得到响应
        # 然后将下面的所有响应头都塞入resp中，然后返回最终的响应
        # 放入的这些信息都是为了后来安全和审计做准备的

        if self.hsts and request.url.scheme == "https":
            v = f"max-age={int(self.hsts_max_age)}"
            if self.include_subdomains:
                v += "; includeSubDomains"
            if self.preload:
                v += "; preload"
            resp.headers["Strict-Transport-Security"] = v

        if self.x_content_type_options:
            resp.headers["X-Content-Type-Options"] = "nosniff"

        if self.x_frame_options:
            resp.headers["X-Frame-Options"] = self.x_frame_options

        if self.referrer_policy:
            resp.headers["Referrer-Policy"] = self.referrer_policy

        if self.permissions_policy:
            resp.headers["Permissions-Policy"] = self.permissions_policy

        if self.csp:
            resp.headers["Content-Security-Policy"] = self.csp

        return resp
