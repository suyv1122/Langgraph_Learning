from typing import Optional

from pydantic import BaseModel, EmailStr


# ----------------- app/main.py -----------------
class ChatReq(BaseModel):
    text: str
    user_role: str = "public"
    requester: str = "anonymous"
    session_id: Optional[str] = None

class ChatResp(BaseModel):
    answer: str
    session_id: Optional[str] = None
    active_route: Optional[str] = None


# ----------------- app/api/auth_api.py -----------------
class RegisterReq(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    phone: Optional[int] = None
    full_name: Optional[str] = None

class LoginReq(BaseModel):
    username: str
    password: str

class TokenResp(BaseModel):
    access_token: str
    token_type: str = 'Bearer'

class UserInDB(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[int] = None
    full_name: Optional[str] = None
    is_active: bool
    is_super_admin: bool