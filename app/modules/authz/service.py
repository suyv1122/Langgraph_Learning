# 7.5
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_err
from app.modules.audit.hook import record
from app.modules.auth.models import Permission, RolePermission, User, UserRoleGrant
from app.modules.authz.scope_keys import scopes_with_global


async def require_perms(  # 权限检查核心函数，没有权限就抛错，并记录审计
    db: AsyncSession,
    *,
    user: User,
    scope_key: str,
    perm_codes: list[str],
) -> None:
    if int(user.is_superadmin) == 1:
        return

    if not perm_codes:  # 没有要求权限则直接通过
        return

    scopes = scopes_with_global(scope_key)  # 计算当前scope + global，让全局授权也能生效

    role_ids = (
        await db.execute(
            select(UserRoleGrant.role_id).where(
                UserRoleGrant.user_id == user.id,
                UserRoleGrant.scope_key.in_(scopes),
            )
        )
    ).scalars().all() # 查用户在这些scopes下有哪些role_id

    if not role_ids:  # 用户在该scope下没有任何role
        record(
            action="rbac.role_required",
            status="deny",
            http_status=403,
            meta={"scope_key": str(scope_key), "user_id": int(user.id)},
            error_code="rbac.role_required",
        )
        raise_err("rbac.role_required", meta={"scope_key": scope_key})

    rows = (  # 再查这些roles命中的权限code
        await db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.perm_id == Permission.id)
            .where(
                RolePermission.role_id.in_(role_ids),
                Permission.code.in_(perm_codes),
            )
        )
    ).scalars().all()

    have = {str(x) for x in rows}  # 转成集合便于差集计算
    missing = [p for p in perm_codes if p not in have]  # 计算缺失的权限列表，保持原顺序便于调试
    if missing:
        record(
            action="rbac.permission_missing",
            status="deny",
            http_status=403,
            meta={"scope_key": str(scope_key), "missing": list(missing), "user_id": int(user.id)},
            error_code="rbac.permission_missing",
        )
        raise_err("rbac.permission_missing", meta={"scope_key": scope_key, "missing": missing})
