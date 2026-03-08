from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.response import ok_no_store
from app.core.api_response import ok
from app.core.errors import raise_err
from app.infra.blob_storage.interface import StorageBackend
from app.infra.celery.celery_app import celery_app
from app.infra.db.deps import get_db
from app.modules.audit.hook import record
from app.modules.auth.models import User
from app.modules.authz.deps import any_permission_required
from app.modules.authz.scope_keys import scope_workspace
from app.modules.kb.consts import ASSET_STATUS_DELETED
from app.modules.kb.deps import get_storage, get_workspace_id_or_400
from app.modules.kb.models import KBAsset, KBChunk
from app.modules.kb.schemas import AssetResp, CreateAssetReq, EnqueueIngestResp, UploadResp
from app.modules.kb.search_schemas import SearchReq, SearchResp, SearchHit
from app.modules.kb.search_service import search_kb
from app.modules.kb.service import compute_upload_digest, create_asset, mark_uploaded
from app.modules.kb.storage_keys import asset_original_key


router = APIRouter(prefix="/kb", tags=["kb"])


def _ws_scope(request: Request) -> str:
    wid = getattr(request.state, "workspace_id", None)
    if wid is None:
        raise_err("error.http", http_status=400, message="workspace_id_required")
    return scope_workspace(int(wid))


KbWriter = any_permission_required("doc.write", "audio.write", "image.write", "project.manage", scope_builder=_ws_scope)
KbReader = any_permission_required("doc.read", "audio.read", "audio.search", "image.read", "ticket.read", scope_builder=_ws_scope)


def _to_asset_resp(a: KBAsset) -> AssetResp:
    return AssetResp(
        id=int(a.id),
        workspace_id=int(a.workspace_id),
        project_id=int(a.project_id) if a.project_id is not None else None,
        created_by=int(a.created_by),
        resource_type=str(a.resource_type),
        resource_id=int(a.resource_id) if a.resource_id is not None else None,
        filename=str(a.filename),
        title=str(a.title) if a.title is not None else None,
        mime_type=str(a.mime_type) if a.mime_type is not None else None,
        source_type=str(a.source_type) if a.source_type is not None else None,
        size_bytes=int(a.size_bytes) if a.size_bytes is not None else None,
        sha256=str(a.sha256) if a.sha256 is not None else None,
        storage_key=str(a.storage_key) if a.storage_key is not None else None,
        status=str(a.status),
        error=str(a.error) if a.error is not None else None,
        meta=dict(a.meta) if a.meta is not None else None,
        created_at=str(a.created_at),
        updated_at=str(a.updated_at),
    )


@router.post("/assets", response_model=dict, status_code=201)
async def create_kb_asset(
    req: CreateAssetReq,
    response: Response,
    request: Request,
    me: User = Depends(KbWriter),
    db: AsyncSession = Depends(get_db),
):
    wid = get_workspace_id_or_400(request)
    a = await create_asset(
        db,
        workspace_id=int(wid),
        project_id=req.project_id,
        created_by=int(me.id),
        filename=req.filename,
        mime_type=req.mime_type,
        title=req.title,
        meta=req.meta,
        resource_type=req.resource_type,
    )
    record(action="kb.asset_create", status="ok", meta={"workspace_id": int(wid), "asset_id": int(a.id), "user_id": int(me.id)})
    return ok_no_store(response, _to_asset_resp(a))


@router.get("/assets", response_model=dict)
async def list_assets(
    request: Request,
    response: Response,
    project_id: int | None = Query(default=None),
    me: User = Depends(KbReader),
    db: AsyncSession = Depends(get_db),
):
    wid = get_workspace_id_or_400(request)
    stmt = select(KBAsset).where(KBAsset.workspace_id == int(wid), KBAsset.status != ASSET_STATUS_DELETED).order_by(KBAsset.id.desc())
    if project_id is not None:
        stmt = stmt.where(KBAsset.project_id == int(project_id))
    rows = (await db.execute(stmt)).scalars().all()
    return ok_no_store(response, [ _to_asset_resp(x) for x in rows ])


@router.post("/assets/{asset_id}/upload", response_model=dict)
async def upload_kb_asset(
    asset_id: int,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    me: User = Depends(KbWriter),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    wid = get_workspace_id_or_400(request)

    a = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
    if not a or int(a.workspace_id) != int(wid) or a.status == ASSET_STATUS_DELETED:
        raise_err("kb.asset_not_found")

    data = await file.read()
    size_bytes, sha = await compute_upload_digest(data)

    key = asset_original_key(workspace_id=int(wid), asset_id=int(asset_id), filename=a.filename)
    await storage.put_bytes(key=key, data=data, content_type=str(file.content_type) if file.content_type else a.mime_type)

    a2 = await mark_uploaded(db, asset_id=int(asset_id), storage_key=key, size_bytes=int(size_bytes), sha256=str(sha))

    record(action="kb.asset_upload", status="ok", meta={"workspace_id": int(wid), "asset_id": int(asset_id), "size_bytes": int(size_bytes), "user_id": int(me.id)})

    return ok_no_store(response, UploadResp(asset_id=int(a2.id), storage_key=str(key), size_bytes=int(size_bytes), sha256=str(sha)))


@router.post("/assets/{asset_id}/ingest", response_model=dict, status_code=202)
async def enqueue_ingest(
    asset_id: int,
    request: Request,
    response: Response,
    me: User = Depends(KbWriter),
    db: AsyncSession = Depends(get_db),
):
    wid = get_workspace_id_or_400(request)

    a = (await db.execute(select(KBAsset).where(KBAsset.id == int(asset_id)))).scalar_one_or_none()
    if not a or int(a.workspace_id) != int(wid) or a.status == ASSET_STATUS_DELETED:
        raise_err("kb.asset_not_found")
    if not a.storage_key:
        raise_err("kb.asset_not_uploaded")

    celery_app.send_task("kb.ingest_asset", args=[int(asset_id)])

    record(action="kb.asset_ingest_enqueued", status="ok", meta={"workspace_id": int(wid), "asset_id": int(asset_id), "user_id": int(me.id)})

    return ok_no_store(response, EnqueueIngestResp(asset_id=int(asset_id)))


@router.post("/search", response_model=dict)
async def search(
    req: SearchReq,
    request: Request,
    response: Response,
    me: User = Depends(KbReader),
    db: AsyncSession = Depends(get_db),
):
    wid = get_workspace_id_or_400(request)
    qdrant = request.app.state.qdrant

    ids = await search_kb(
        db,
        qdrant=qdrant,
        workspace_id=int(wid),
        project_id=req.project_id,
        query=req.q,
        mode=req.mode,
        top_k=req.top_k,
    )
    if not ids:
        return ok_no_store(response, SearchResp(q=req.q, mode=req.mode, top_k=int(req.top_k), items=[]))

    want = [int(x[0]) for x in ids]
    rows = (await db.execute(select(KBChunk).where(KBChunk.workspace_id == int(wid), KBChunk.id.in_(want)))).scalars().all()
    by_id = {int(x.id): x for x in rows}

    items: list[SearchHit] = []
    for cid, score, sources in ids:
        ch = by_id.get(int(cid))
        if not ch:
            continue
        items.append(
            SearchHit(
                chunk_id=int(ch.id),
                asset_id=int(ch.asset_id),
                score=float(score),
                sources=list(sources),
                content=str(ch.content),
            )
        )

    record(action="kb.search", status="ok", meta={"workspace_id": int(wid), "mode": str(req.mode), "top_k": int(req.top_k), "returned": int(len(items))})
    return ok_no_store(response, SearchResp(q=req.q, mode=req.mode, top_k=int(req.top_k), items=items))