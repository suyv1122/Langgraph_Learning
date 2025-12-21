from datetime import datetime

from app.db.mysql import get_conn
from app.model.auth_model import RegisterReq
from app.service.auth_service import hash_password


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