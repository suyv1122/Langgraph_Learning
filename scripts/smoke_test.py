from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

try:
    import asyncpg  # type: ignore
except Exception:
    asyncpg = None


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str


def _hdr(access_token: str, workspace_id: int | None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {access_token}"}
    if workspace_id is not None:
        h["X-Workspace-Id"] = str(int(workspace_id))
    return h


def _pp(title: str, obj: Any) -> None:
    print(f"\n=== {title} ===")
    print(obj)


def _normalize_pg_url(db_url: str) -> str:
    return db_url.replace("postgresql+asyncpg://", "postgresql://").strip()


def _extract_request_id(resp: httpx.Response) -> Optional[str]:
    try:
        j = resp.json()
        return j.get("error", {}).get("request_id")
    except Exception:
        return None


async def _expect_status(resp: httpx.Response, want: int) -> None:
    if resp.status_code != want:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        rid = _extract_request_id(resp)
        extra = f" request_id={rid}" if rid else ""
        raise RuntimeError(f"Unexpected status {resp.status_code}, want {want}.{extra} Body={body}")


async def _req(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    workspace_id: int | None = None,
    access_token: str | None = None,
    json: Any | None = None,
    params: dict[str, str] | None = None,
) -> httpx.Response:
    h: dict[str, str] = {}
    p: dict[str, str] = dict(params or {})

    if workspace_id is not None:
        h["X-Workspace-Id"] = str(int(workspace_id))
        p.setdefault("workspace_id", str(int(workspace_id)))

    if access_token is not None:
        h["Authorization"] = f"Bearer {access_token}"

    r = await client.request(method, path, headers=h or None, params=p or None, json=json)
    return r


async def health_checks(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz")
    await _expect_status(r, 200)
    _pp("healthz", r.json())

    r = await client.get("/readyz")
    await _expect_status(r, 200)
    _pp("readyz", r.json())

    r = await client.get("/version")
    await _expect_status(r, 200)
    _pp("version", r.json())


async def register(
    client: httpx.AsyncClient,
    email: str,
    password: str,
    *,
    workspace_id: int | None,
) -> dict[str, Any]:
    body = {"email": email, "password": password}
    if workspace_id is not None:
        body["workspace_id"] = int(workspace_id)

    r = await _req(client, "POST", "/auth/register", workspace_id=workspace_id, json=body)

    if r.status_code == 409:
        _pp(f"register (already exists) ws={workspace_id}", r.json())
        return {"already_exists": True}

    if r.status_code != 201:
        try:
            body2 = r.json()
        except Exception:
            body2 = r.text
        rid = _extract_request_id(r)
        print("\n❌ /auth/register failed")
        print(f"status={r.status_code} request_id={rid} ws={workspace_id}")
        print(f"body={body2}")
        print("\n👉 去跑 uvicorn 的终端里搜索这个 request_id，看真实异常堆栈。")
        await _expect_status(r, 201)

    data = r.json()
    _pp(f"register ws={workspace_id}", data)
    return data


async def login(
    client: httpx.AsyncClient,
    email: str,
    password: str,
    *,
    workspace_id: int | None,
) -> Tokens:
    body = {"email": email, "password": password}
    if workspace_id is not None:
        body["workspace_id"] = int(workspace_id)

    r = await _req(client, "POST", "/auth/login", workspace_id=workspace_id, json=body)
    await _expect_status(r, 200)

    j = r.json()
    _pp(f"login ws={workspace_id}", j)
    tok = j["data"]
    return Tokens(access_token=tok["access_token"], refresh_token=tok["refresh_token"])


async def me(client: httpx.AsyncClient, access_token: str, *, workspace_id: int | None) -> dict[str, Any]:
    r = await _req(client, "GET", "/auth/me", workspace_id=workspace_id, access_token=access_token)
    await _expect_status(r, 200)
    j = r.json()
    _pp(f"me ws={workspace_id}", j)
    return j


async def admin_grant_role(
    client: httpx.AsyncClient,
    admin_access: str,
    *,
    workspace_id: int | None,
    user_id: int,
    role_name: str,
    scope_key: str,
) -> dict[str, Any]:
    payload = {"user_id": int(user_id), "role_name": role_name, "scope_key": scope_key}
    r = await _req(
        client,
        "POST",
        "/admin/grants",
        workspace_id=workspace_id,
        access_token=admin_access,
        json=payload,
    )

    if r.status_code != 201:
        try:
            body = r.json()
        except Exception:
            body = r.text
        rid = _extract_request_id(r)
        print("\n❌ /admin/grants failed")
        print(f"status={r.status_code} request_id={rid} ws={workspace_id}")
        print(f"body={body}")
        print("\n👉 去跑 uvicorn 的终端里搜索这个 request_id，看真实异常堆栈。")
        raise RuntimeError(f"/admin/grants failed status={r.status_code} request_id={rid}")

    j = r.json()
    _pp(f"admin grant role ws={workspace_id} role={role_name} user_id={user_id} scope={scope_key}", j)
    return j


async def admin_list_grants(
    client: httpx.AsyncClient,
    admin_access: str,
    *,
    workspace_id: int | None,
    user_id: int | None = None,
) -> dict[str, Any]:
    params: dict[str, str] = {}
    if user_id is not None:
        params["user_id"] = str(int(user_id))

    r = await _req(
        client,
        "GET",
        "/admin/grants",
        workspace_id=workspace_id,
        access_token=admin_access,
        params=params,
    )
    await _expect_status(r, 200)
    j = r.json()
    _pp(f"admin list grants ws={workspace_id}", j)
    return j


async def expect_forbidden_admin_list(
    client: httpx.AsyncClient,
    access_token: str,
    *,
    workspace_id: int | None,
) -> None:
    r = await _req(client, "GET", "/admin/grants", workspace_id=workspace_id, access_token=access_token)
    if r.status_code != 403:
        try:
            body = r.json()
        except Exception:
            body = r.text
        rid = _extract_request_id(r)
        raise RuntimeError(f"Expected 403, got {r.status_code} request_id={rid} ws={workspace_id}. Body={body}")
    _pp(f"non-admin calling /admin/grants -> expected 403 ws={workspace_id}", r.json())


async def bootstrap_make_superadmin(db_url: str, email: str) -> None:
    if asyncpg is None:
        raise RuntimeError("asyncpg not installed. Run: pip install asyncpg")

    url = _normalize_pg_url(db_url)
    if not url:
        raise RuntimeError("DATABASE_URL is empty. Put DATABASE_URL in .env to enable bootstrap.")

    conn = await asyncpg.connect(url)
    try:
        res = await conn.execute(
            "UPDATE users SET is_superadmin = TRUE, is_active = TRUE WHERE email = $1",
            email,
        )
        n = int(res.split()[-1])
        if n <= 0:
            raise RuntimeError(f"bootstrap failed: user not found in DB for email={email!r}")

        row = await conn.fetchrow("SELECT id, email, is_active, is_superadmin FROM users WHERE email = $1", email)
        _pp("bootstrap superadmin", dict(row) if row else None)
    finally:
        await conn.close()


async def bootstrap_seed_authz_if_empty(db_url: str) -> None:
    if asyncpg is None:
        raise RuntimeError("asyncpg not installed. Run: pip install asyncpg")

    url = _normalize_pg_url(db_url)
    if not url:
        raise RuntimeError("DATABASE_URL is empty. Put DATABASE_URL in .env to enable bootstrap.")

    ROLES = (
        ("owner", "Workspace/Project owner"),
        ("admin", "Workspace/Project admin"),
        ("editor", "Can create/update resources"),
        ("viewer", "Read-only access"),
    )

    PERMISSIONS = (
        ("workspace.manage", "Manage workspace settings/members"),
        ("project.manage", "Manage projects"),
        ("doc.read", "Read documents"),
        ("doc.write", "Create/update documents"),
        ("doc.delete", "Delete documents"),
        ("audio.read", "Read audio resources"),
        ("audio.search", "Search audio content"),
        ("audio.write", "Upload/update audio"),
        ("audio.delete", "Delete audio"),
        ("image.read", "Read images"),
        ("image.write", "Upload/update images"),
        ("image.delete", "Delete images"),
        ("ticket.read", "Read tickets"),
        ("ticket.create", "Create tickets"),
        ("ticket.approve", "Approve tickets"),
        ("ticket.close", "Close tickets"),
    )

    all_perm_codes = tuple(code for code, _ in PERMISSIONS)

    DEFAULT_ROLE_PERMS = {
        "owner": all_perm_codes,
        "admin": all_perm_codes,
        "editor": (
            "doc.read",
            "doc.write",
            "audio.read",
            "audio.search",
            "audio.write",
            "image.read",
            "image.write",
            "ticket.read",
            "ticket.create",
        ),
        "viewer": (
            "doc.read",
            "audio.read",
            "audio.search",
            "image.read",
            "ticket.read",
        ),
    }

    conn = await asyncpg.connect(url)
    try:
        n_roles = await conn.fetchval("SELECT COUNT(*) FROM roles")
        if int(n_roles or 0) > 0:
            _pp("authz seed", "roles already seeded, skip")
            return

        async with conn.transaction():
            for name, desc in ROLES:
                await conn.execute(
                    """
                    INSERT INTO roles(name, description)
                    VALUES ($1, $2)
                    ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                    """,
                    name,
                    desc,
                )

            for code, desc in PERMISSIONS:
                await conn.execute(
                    """
                    INSERT INTO permissions(code, description)
                    VALUES ($1, $2)
                    ON CONFLICT (code) DO UPDATE SET description = EXCLUDED.description
                    """,
                    code,
                    desc,
                )

            role_rows = await conn.fetch("SELECT id, name FROM roles")
            perm_rows = await conn.fetch("SELECT id, code FROM permissions")
            role_map = {str(r["name"]): int(r["id"]) for r in role_rows}
            perm_map = {str(p["code"]): int(p["id"]) for p in perm_rows}

            for role_name, perm_codes in DEFAULT_ROLE_PERMS.items():
                rid = role_map.get(role_name)
                if rid is None:
                    continue
                for code in perm_codes:
                    pid = perm_map.get(code)
                    if pid is None:
                        continue
                    await conn.execute(
                        """
                        INSERT INTO role_permissions(role_id, perm_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                        """,
                        rid,
                        pid,
                    )

        _pp("authz seed", "seeded roles/permissions/role_permissions OK")
    finally:
        await conn.close()


async def bootstrap_create_workspace(db_url: str, name: str, desc: str | None = None) -> int:
    if asyncpg is None:
        raise RuntimeError("asyncpg not installed. Run: pip install asyncpg")

    url = _normalize_pg_url(db_url)
    if not url:
        raise RuntimeError("DATABASE_URL is empty. Put DATABASE_URL in .env to enable bootstrap.")

    conn = await asyncpg.connect(url)
    try:
        row = await conn.fetchrow("SELECT id, name FROM workspaces WHERE name=$1", name)
        if row:
            wid = int(row["id"])
            _pp("workspace exists", {"id": wid, "name": str(row["name"])})
            return wid

        row2 = await conn.fetchrow(
            """
            INSERT INTO workspaces(name, description)
            VALUES ($1, $2)
            RETURNING id, name
            """,
            name,
            desc,
        )
        if not row2:
            raise RuntimeError("create workspace failed: no returning row")
        wid = int(row2["id"])
        _pp("workspace created", {"id": wid, "name": str(row2["name"])})
        return wid
    finally:
        await conn.close()


async def ensure_global_workspace_manage_grant(db_url: str, admin_email: str) -> str:
    if asyncpg is None:
        raise RuntimeError("asyncpg not installed. Run: pip install asyncpg")

    url = _normalize_pg_url(db_url)
    conn = await asyncpg.connect(url)
    try:
        uid = await conn.fetchval("SELECT id FROM users WHERE email = $1", admin_email)
        if uid is None:
            raise RuntimeError(f"ensure_grant failed: user not found email={admin_email!r}")
        uid = int(uid)

        rows = await conn.fetch("SELECT id, name FROM roles ORDER BY id ASC")
        if not rows:
            raise RuntimeError("ensure_grant failed: no roles in DB")

        role_name = None
        role_id = None
        for r in rows:
            if str(r["name"]) == "owner":
                role_name = "owner"
                role_id = int(r["id"])
                break
        if role_id is None:
            role_name = str(rows[0]["name"])
            role_id = int(rows[0]["id"])

        has_workspace_manage = await conn.fetchval(
            """
            SELECT 1
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.perm_id
            WHERE rp.role_id = $1 AND p.code = 'workspace.manage'
            LIMIT 1
            """,
            role_id,
        )
        if has_workspace_manage is None:
            for r in rows:
                rid = int(r["id"])
                ok = await conn.fetchval(
                    """
                    SELECT 1
                    FROM role_permissions rp
                    JOIN permissions p ON p.id = rp.perm_id
                    WHERE rp.role_id = $1 AND p.code = 'workspace.manage'
                    LIMIT 1
                    """,
                    rid,
                )
                if ok is not None:
                    role_name = str(r["name"])
                    role_id = rid
                    break

        if role_id is None:
            raise RuntimeError("ensure_grant failed: cannot find any role with workspace.manage")

        exists = await conn.fetchval(
            """
            SELECT 1
            FROM user_role_grants
            WHERE user_id=$1 AND role_id=$2 AND scope_key='global'
            LIMIT 1
            """,
            uid,
            role_id,
        )
        if exists is not None:
            _pp("ensure global admin grant", {"user_id": uid, "role_name": role_name, "scope_key": "global", "idempotent": True})
            return str(role_name)

        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO user_role_grants(user_id, role_id, scope_key, created_by)
                VALUES ($1, $2, 'global', $1)
                ON CONFLICT (user_id, role_id, scope_key) DO NOTHING
                """,
                uid,
                role_id,
            )

        _pp("ensure global admin grant", {"user_id": uid, "role_name": role_name, "scope_key": "global", "idempotent": False})
        return str(role_name)
    finally:
        await conn.close()


async def assert_grants_not_empty(db_url: str) -> None:
    if asyncpg is None:
        raise RuntimeError("asyncpg not installed. Run: pip install asyncpg")

    url = _normalize_pg_url(db_url)
    conn = await asyncpg.connect(url)
    try:
        n = await conn.fetchval("SELECT COUNT(*) FROM user_role_grants")
        _pp("user_role_grants count", int(n or 0))
        if int(n or 0) <= 0:
            raise RuntimeError("user_role_grants is empty after smoke test")
    finally:
        await conn.close()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:8000"))

    ap.add_argument("--admin-email", default=os.getenv("ADMIN_EMAIL", "admin@example.com"))
    ap.add_argument("--admin-pass", default=os.getenv("ADMIN_PASS", "Password123!"))

    ap.add_argument("--user-email", default=os.getenv("USER_EMAIL", "user1@example.com"))
    ap.add_argument("--user-pass", default=os.getenv("USER_PASS", "Password123!"))

    ap.add_argument("--db-url", default=os.getenv("DATABASE_URL", ""))

    ap.add_argument("--ws1-name", default=os.getenv("WS1_NAME", "ws1"))
    ap.add_argument("--ws2-name", default=os.getenv("WS2_NAME", "ws2"))

    ap.add_argument("--scope-key", default=os.getenv("SCOPE_KEY", "global"))
    args = ap.parse_args()

    if not args.db_url.strip():
        raise RuntimeError(
            "This smoke_test requires DATABASE_URL.\n"
            "Put DATABASE_URL in .env (postgresql+asyncpg://... is OK)."
        )

    ws1 = await bootstrap_create_workspace(args.db_url, args.ws1_name, "smoke ws1")
    ws2 = await bootstrap_create_workspace(args.db_url, args.ws2_name, "smoke ws2")

    async with httpx.AsyncClient(base_url=args.base_url, timeout=20.0) as client:
        await health_checks(client)

        await register(client, args.admin_email, args.admin_pass, workspace_id=ws1)
        await bootstrap_make_superadmin(args.db_url, args.admin_email)
        await bootstrap_seed_authz_if_empty(args.db_url)
        ensured_role_name = await ensure_global_workspace_manage_grant(args.db_url, args.admin_email)
        _pp("ensured admin RBAC", {"role_name": ensured_role_name, "scope_key": "global"})

        admin_tokens = await login(client, args.admin_email, args.admin_pass, workspace_id=ws1)
        admin_me = await me(client, admin_tokens.access_token, workspace_id=ws1)
        admin_user_id = int(admin_me["data"]["id"])

        if not bool(admin_me["data"].get("is_superadmin")):
            raise RuntimeError(
                "Bootstrap set is_superadmin in DB, but /auth/me still returns is_superadmin=False.\n"
                "Check DATABASE_URL points to the same DB your app is using."
            )

        await admin_grant_role(
            client,
            admin_tokens.access_token,
            workspace_id=ws1,
            user_id=admin_user_id,
            role_name="owner",
            scope_key=args.scope_key,
        )
        await admin_list_grants(client, admin_tokens.access_token, workspace_id=ws1, user_id=admin_user_id)

        await register(client, args.user_email, args.user_pass, workspace_id=ws1)
        user_tokens_ws1 = await login(client, args.user_email, args.user_pass, workspace_id=ws1)
        await expect_forbidden_admin_list(client, user_tokens_ws1.access_token, workspace_id=ws1)

        email2 = args.user_email
        pass2 = args.user_pass
        await register(client, email2, pass2, workspace_id=ws2)
        user_tokens_ws2 = await login(client, email2, pass2, workspace_id=ws2)
        await expect_forbidden_admin_list(client, user_tokens_ws2.access_token, workspace_id=ws2)

    await assert_grants_not_empty(args.db_url)
    print("\n✅ smoke test finished OK")


if __name__ == "__main__":
    asyncio.run(main())