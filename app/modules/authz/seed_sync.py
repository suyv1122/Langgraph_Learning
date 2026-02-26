# 7.4
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Permission, Role, RolePermission
from app.modules.authz.seed import DEFAULT_ROLE_PERMS, PERMISSIONS, ROLES


async def sync_authz(db: AsyncSession) -> None:
# 把seed.py中的roles/permissions同步进数据库，并补齐默认role-perm映射
    async with db.begin():
        for name, desc in ROLES:
            stmt = (
                pg_insert(Role)
                .values(name=str(name), description=str(desc))
                .on_conflict_do_update(
                    index_elements=[Role.name],
                    set_={"description": str(desc)},
                )
            )
            await db.execute(stmt)

        for code, desc in PERMISSIONS:
            stmt = (
                pg_insert(Permission)
                .values(code=str(code), description=str(desc))
                .on_conflict_do_update(
                    index_elements=[Permission.code],
                    set_={"description": str(desc)},
                )
            )
            await db.execute(stmt)

        role_rows = (await db.execute(select(Role))).scalars().all()
        perm_rows = (await db.execute(select(Permission))).scalars().all()

        role_map = {str(r.name): int(r.id) for r in role_rows}
        perm_map = {str(p.code): int(p.id) for p in perm_rows}

        existing = set((await db.execute(select(RolePermission.role_id, RolePermission.perm_id))).all())

        for role_name, perm_codes in DEFAULT_ROLE_PERMS.items():
            rid = role_map.get(str(role_name))
            if rid is None:
                continue
            for code in perm_codes:
                pid = perm_map.get(str(code))
                if pid is None:
                    continue
                if (rid, pid) in existing:
                    continue
                db.add(RolePermission(role_id=int(rid), perm_id=int(pid)))
