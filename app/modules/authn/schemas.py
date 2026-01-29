# 模式类，有些类似models
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class TokenResp(BaseModel):  # 登录和刷新返回token的响应体
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    refresh_token: str


class RefreshReq(BaseModel):  # 刷新和登出请求体
    refresh_token: str


class MeResp(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_superadmin: bool
