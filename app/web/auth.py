from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr

from app.db.mysql import get_conn
from app.security.security import hash_password, verify_password, create_access_token, decode_token

router =APIRouter(prefix='/auth', tags=['auth'])

# TODO: 为基础模型归类并单独设置文件夹
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


# ---------------------- DB helpers -----------------------

def get_user_by_username(username: str) -> dict | None:
    sql = 'select * from users where username=%s limit 1'
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (username,))
            return cursor.fetchone()

def create_user(data: RegisterReq) -> dict:
    pwd_hash = hash_password(data.password)
    sql ="""
    insert into users (
        username, email, phone, password_hash, 
        full_name, is_active, is_super_admin) 
    values (%s, %s, %s, %s, %s, 1, 0)
    """
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (data.username, data.email, data.phone, pwd_hash, data.full_name))
            user_id = cursor.lastrowid

    # 默认给予public角色，超级管理员不应通过注册得到
    sql_bind = '''
    insert ignore into user_roles(user_id, role_id)
    select %s, r.id from roles r where r.code='public'
    '''
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_bind,(user_id,))

    u = get_user_by_username(data.username)
    assert u is not None
    return u

def update_last_login(user_id: int):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute('update users set last_login_at=%s where id=%s', (datetime.now(), user_id))


# ---------------------- Dependencies -----------------------

def get_current_user(authorization: str | None = Header(default=None)) -> UserInDB:
    if not authorization or not authorization.lower().startswith('bearer'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing Bearer token')

    token = authorization.split('', 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    username = payload.get('sub')
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token payload')

    u = get_user_by_username(username)
    if not u or not u.get('is_active'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found or disabled')

    return UserInDB(
        id=int(u['id']),
        username=u['username'],
        email=u.get('email'),
        phone=u.get('phone'),
        full_name=u.get('full_name'),
        is_active=u.get('is_active'),
        is_super_admin=bool(u['is_super_admin'])
    )

def get_current_user_optional(authorization: str | None = Header(default=None)) -> UserInDB | None:
    if not authorization:
        return None
    if not authorization.lower().startswith('bearer'):
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None


# ---------------------- Routes -----------------------

@router.post('/register', response_model=UserInDB)
def register(req: RegisterReq):
    if get_user_by_username(req.username):
        raise HTTPException(status_code=400, detail='Username already exists')
    u = create_user(req)
    return UserInDB(
        id=int(u['id']),
        username=u['username'],
        email=u.get('email'),
        phone=u.get('phone'),
        full_name=u.get('full_name'),
        is_active=bool(u['is_active']),
        is_super_admin=bool(u['is_super_admin'])
    )

@router.post('/login', response_model=TokenResp)
def login(req: LoginReq):
    u =get_user_by_username(req.username)
    if not u:
        raise HTTPException(status_code=401, detail='bad credentials')

    if not verify_password(req.password, u['password_hash']):
        raise HTTPException(status_code=401, detail='bad credentials')

    if not u.get('is_active'):
        raise HTTPException(status_code=403, detail='user disabled')

    update_last_login(int(u['id']))
    token = create_access_token({'usb':u['username'], 'uid':int(u['id'])})
    return TokenResp(access_token=token)

@router.get('/me', response_model=UserInDB)
def me(current_user: UserInDB = Depends(get_current_user)):
    return current_user