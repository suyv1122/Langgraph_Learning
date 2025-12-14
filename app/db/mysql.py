# todo: 之后根据类型拆分不同项目下的数据库文件
import os
import pymysql
from contextlib import contextmanager

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'paradice')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '1598745632')
MYSQL_DB = os.getenv('MYSQL_DB', 'Leave_Request')

@contextmanager
def get_conn():
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4',
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        yield conn
    finally:
        conn.close()


def get_leave_balance(requester: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT annual_days, sick_days, personal_days FROM leave_balances WHERE requester=%s',
                (requester,)
            )
            return cur.fetchone()


def insert_leave_request(req: dict) -> str:
    """
    req expects keys: leave_id, requester, leave_type, start_time, end_time, duration_days, reason
    """
    with get_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO leave_requests
                    (leave_id, requester, leave_type, start_time, end_time, duration_days, reason, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDING')
                    """,
                    (
                        req['leave_id'],
                        req['requester'],
                        req['leave_type'],
                        req['start_time'],
                        req['end_time'],
                        req['duration_days'],
                        req['reason']
                    )
                )
        except Exception as e:
            print("[DB ERROR] insert_leave_request failed:", repr(e))
            raise
        return req['leave_id']


def get_leave_request(leave_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM leave_requests WHERE leave_id=%s', (leave_id,))
            return cur.fetchone()


def cancel_leave_request(leave_id: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE leave_requests SET status="CANCELLED" WHERE leave_id=%s AND status="PENDING"',
                (leave_id,)
            )
            return cur.rowcount > 0


def get_recent_leave_requests(requester: str, limit: int = 5) -> list[dict]:
    limit = max(1, min(int(limit), 20)) # 执行查询请求时最多一次查询前20条
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT leave_id, leave_type, start_time, end_time, duration_days, reason, status, created_at'
                'FROM leave_requests where requester=%s'
                'order by id desc limit %s',
                (requester, limit)
            )
            return cur.fetchall()


def update_leave_request(leave_id: str, fields: dict) -> bool:
    """
    Only update PENDING requests.
    fields can include: leave_type, start_time, end_time, duration_days, reason
    """
    """
    仅更新待处理的请求。
    字段可包含：离开类型、开始时间、结束时间、持续时间（天数）、原因
    """
    allowed = {'leave_type', 'start_time', 'end_time', 'duration_days', 'reason'}
    sets = []
    params =[]
    for k, v in fields.items():
        if k in allowed and v is not None:
            sets.append(f'{k}=%s')  # sets = ['leave_type=%s', 'end_time=%s']
            params.append(v)        # params = ['年假', 'xx年月日']

    if not sets:
        return False

    params.extend([leave_id])
    sql = (
        'update leave_requests set ' + ','.join(sets) +
        ' where leave_id=%s and status="PENDING"'
    )

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.rowcount > 0