from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_err
from app.modules.audit.hook import record
from app.modules.resources.models import Project, Resource, Workspace


async def create_workspace(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
) -> Workspace:
    async with db.begin():
        exists = (await db.execute(select(Workspace.id).where(Workspace.name == name))).scalar_one_or_none()
        if exists:
            raise_err("resources.workspace_name_taken")
        ws = Workspace(name=str(name), description=str(description) if description is not None else None)
        db.add(ws)
        await db.flush()
        await db.refresh(ws)

    record(action="resources.workspace_create", status="ok", meta={"workspace_id": int(ws.id), "name": str(ws.name)})
    return ws


async def create_project(
    db: AsyncSession,
    *,
    workspace_id: int,
    name: str,
    description: str | None,
) -> Project:
    ws = (await db.execute(select(Workspace).where(Workspace.id == int(workspace_id)))).scalar_one_or_none()
    if not ws:
        raise_err("resources.workspace_not_found")

    async with db.begin():
        exists = (
            (await db.execute(select(Project.id).where(Project.workspace_id == int(workspace_id), Project.name == name)))
            .scalar_one_or_none()
        )
        if exists:
            raise_err("resources.project_name_taken")
        p = Project(workspace_id=int(workspace_id), name=str(name), description=str(description) if description else None)
        db.add(p)
        await db.flush()
        await db.refresh(p)

    record(
        action="resources.project_create",
        status="ok",
        meta={"workspace_id": int(workspace_id), "project_id": int(p.id), "name": str(p.name)},
    )
    return p


async def ensure_resource_dir(  # 确认资源条目是否存在，存在则建立，不存在则返回
    db: AsyncSession,
    *,
    workspace_id: int,
    project_id: int | None,
    resource_type: str,
    ref_id: int,
    created_by: int,
) -> Resource:
    rt = str(resource_type or "").strip()
    if not rt or ":" in rt or len(rt) > 32:
        raise_err("kb.asset_bad_resource_type")

    async with db.begin():
        exists = (
            (
                await db.execute(
                    select(Resource).where(
                        Resource.workspace_id == int(workspace_id),
                        Resource.project_id.is_(None) if project_id is None else Resource.project_id == int(project_id),
                        Resource.resource_type == rt,
                        Resource.ref_id == int(ref_id),
                    )
                )
            )
            .scalars()
            .first()
        )
        if exists:
            return exists

        r = Resource(
            workspace_id=int(workspace_id),
            project_id=int(project_id) if project_id is not None else None,
            resource_type=str(rt),
            ref_id=int(ref_id),
            created_by=int(created_by),
        )
        db.add(r)
        await db.flush()
        await db.refresh(r)

    record(
        action="resources.resource_dir_upsert",
        status="ok",
        meta={
            "workspace_id": int(workspace_id),
            "project_id": int(project_id) if project_id is not None else None,
            "resource_type": str(rt),
            "ref_id": int(ref_id),
            "resource_id": int(r.id),
        },
    )
    return r