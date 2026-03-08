from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ok
from app.core.api_schemas import ApiResponse
from app.core.errors import raise_err
from app.infra.db.deps import get_db
from app.modules.admin.schemas import GrantRoleData, GrantRoleReq, GrantRow, ListGrantsResp, RevokeRoleData
from app.modules.audit.hook import record
from app.modules.auth.models import Role, User, UserRoleGrant
from app.modules.authz.deps import permission_required
from app.modules.authz.scope_keys import parse_scope_key, scope_global, scope_project, scope_workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _global_scope(_request) -> str:
    return scope_global()


AdminUser = permission_required("workspace.manage", scope_builder=_global_scope)


def _normalize_scope(scope_key: str, workspace_id: int | None, project_id: int | None) -> str:
    if workspace_id is not None and int(workspace_id) > 0:
        return scope_workspace(int(workspace_id))
    if project_id is not None and int(project_id) > 0:
        return scope_project(int(project_id))
    sk = str(scope_key or "").strip()
    if not sk:
        raise_err("error.http", http_status=422, message="scope_key_required")
    try:
        parse_scope_key(sk)
    except Exception:
        raise_err("error.http", http_status=422, message="bad_scope_key")
    return sk


@router.post("/grants", response_model=ApiResponse[GrantRoleData], status_code=201)
async def grant_role(
    req: GrantRoleReq,
    me: User = Depends(AdminUser),
    db: AsyncSession = Depends(get_db),
    workspace_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
):
    sk = _normalize_scope(req.scope_key, workspace_id, project_id)

    role = (await db.execute(select(Role).where(Role.name == req.role_name))).scalar_one_or_none()
    if not role:
        record(action="admin.grant_role", status="deny", http_status=404, meta={"reason": "role_not_found", "role_name": str(req.role_name), "scope_key": str(sk), "target_user_id": int(req.user_id), "actor_user_id": int(me.id)}, error_code="admin.role_not_found")
        raise_err("admin.role_not_found")

    target = (await db.execute(select(User).where(User.id == req.user_id))).scalar_one_or_none()
    if not target:
        record(action="admin.grant_role", status="deny", http_status=404, meta={"reason": "user_not_found", "role_name": str(req.role_name), "scope_key": str(sk), "target_user_id": int(req.user_id), "actor_user_id": int(me.id)}, error_code="admin.user_not_found")
        raise_err("admin.user_not_found")

    exists = (await db.execute(select(UserRoleGrant.id).where(UserRoleGrant.user_id == req.user_id, UserRoleGrant.role_id == role.id, UserRoleGrant.scope_key == sk))).scalar_one_or_none()
    if exists:
        record(action="admin.grant_role", status="ok", meta={"idempotent": True, "role_name": str(req.role_name), "scope_key": str(sk), "target_user_id": int(req.user_id), "actor_user_id": int(me.id)})
        return ok(GrantRoleData(granted=True, idempotent=True))

    try:
        stmt = (
            pg_insert(UserRoleGrant)
            .values(user_id=int(req.user_id), role_id=int(role.id), scope_key=str(sk), created_by=int(me.id))
            .on_conflict_do_nothing(index_elements=[UserRoleGrant.user_id, UserRoleGrant.role_id, UserRoleGrant.scope_key])
        )
        async with db.begin():
            res = await db.execute(stmt)

        rc = int(getattr(res, "rowcount", 0) or 0)
        idempotent = (rc == 0)

        record(action="admin.grant_role", status="ok", meta={"idempotent": bool(idempotent), "role_name": str(req.role_name), "scope_key": str(sk), "target_user_id": int(req.user_id), "actor_user_id": int(me.id)})
        return ok(GrantRoleData(granted=True, idempotent=idempotent))
    except Exception:
        logger.exception("grant_role unexpected error")
        record(action="admin.grant_role", status="error", http_status=500, meta={"role_name": str(req.role_name), "scope_key": str(sk), "target_user_id": int(req.user_id), "actor_user_id": int(me.id)}, error_code="storage.db_error")
        raise_err("storage.db_error")