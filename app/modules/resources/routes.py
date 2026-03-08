from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.response import ok_no_store
from app.core.api_response import ok
from app.core.api_schemas import ApiResponse
from app.core.errors import raise_err
from app.infra.db.deps import get_db
from app.modules.auth.models import User
from app.modules.authn.deps import get_current_user
from app.modules.authz.deps import permission_required
from app.modules.authz.scope_keys import scope_global, scope_workspace
from app.modules.resources.models import Project, Workspace
from app.modules.resources.schemas import (
    CreateProjectReq,
    CreateWorkspaceReq,
    ProjectResp,
    WorkspaceResp,
)
from app.modules.resources.service import create_project, create_workspace


router = APIRouter(tags=["resources"])


def _global_scope(_request) -> str:
    return scope_global()


def _ws_scope(request: Request) -> str:
    wid = request.query_params.get("workspace_id") or request.headers.get("X-Workspace-Id")
    try:
        wid_i = int(wid) if wid is not None else 0
    except Exception:
        wid_i = 0
    if wid_i <= 0:
        raise_err("error.http", http_status=400, message="workspace_id_required")
    return scope_workspace(int(wid_i))


AdminGlobal = permission_required("workspace.manage", scope_builder=_global_scope)
WsManager = permission_required("workspace.manage", scope_builder=_ws_scope)


def _ws_resp(x: Workspace) -> WorkspaceResp:
    return WorkspaceResp(
        id=int(x.id),
        name=str(x.name),
        description=str(x.description) if x.description is not None else None,
        created_at=str(x.created_at),
        updated_at=str(x.updated_at),
    )


def _proj_resp(x: Project) -> ProjectResp:
    return ProjectResp(
        id=int(x.id),
        workspace_id=int(x.workspace_id),
        name=str(x.name),
        description=str(x.description) if x.description is not None else None,
        created_at=str(x.created_at),
        updated_at=str(x.updated_at),
    )


@router.post("/workspaces", response_model=ApiResponse[WorkspaceResp], status_code=201)
async def create_ws(
    req: CreateWorkspaceReq,
    response: Response,
    _me: User = Depends(AdminGlobal),
    db: AsyncSession = Depends(get_db),
):
    ws = await create_workspace(db, name=req.name, description=req.description)
    return ok_no_store(response, _ws_resp(ws))


@router.get("/workspaces", response_model=ApiResponse[list[WorkspaceResp]])
async def list_ws(
    response: Response,
    _me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Workspace).order_by(Workspace.id.desc()))).scalars().all()
    return ok_no_store(response, [ _ws_resp(x) for x in rows ])


@router.post("/projects", response_model=ApiResponse[ProjectResp], status_code=201)
async def create_proj(
    req: CreateProjectReq,
    response: Response,
    _me: User = Depends(WsManager),
    db: AsyncSession = Depends(get_db),
):
    p = await create_project(db, workspace_id=int(req.workspace_id), name=req.name, description=req.description)
    return ok_no_store(response, _proj_resp(p))


@router.get("/projects", response_model=ApiResponse[list[ProjectResp]])
async def list_projects(
    workspace_id: int = Query(...),
    response: Response = None,
    _me: User = Depends(WsManager),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        (await db.execute(select(Project).where(Project.workspace_id == int(workspace_id)).order_by(Project.id.desc())))
        .scalars()
        .all()
    )
    return ok_no_store(response, [ _proj_resp(x) for x in rows ])