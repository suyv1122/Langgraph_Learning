from __future__ import annotations

from app.infra.celery.celery_app import celery_app
from app.modules.kb.ingestion.pipeline import run_ingestion
from app.workers.main import get_state
from app.workers.utils import run_async


@celery_app.task(name="kb.ingest_asset")
def ingest_asset(asset_id: int) -> dict:
    st = get_state()
    run_async(run_ingestion(session_maker=st.db_session_maker, asset_id=int(asset_id)))
    return {"ok": True, "asset_id": int(asset_id)}