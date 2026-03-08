from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_setup import setup_logging
from app.infra.blob_storage.local_fs import LocalFsStorage
from app.infra.db.engine import create_engine
from app.infra.db.session import create_session_maker
from app.infra.qdrant_client import create_qdrant_client
from app.infra.celery.celery_app import celery_app
from app.modules.kb.ingest_service import ingest_asset


@celery_app.task(name="kb.ingest_asset")
def ingest_asset_task(asset_id: int) -> dict:
    setup_logging(level=settings.log_level)

    async def _run() -> dict:   # 这里是一个桥接，可能是接口设计错了(ingest_asset_task 他们是同步任务), 所以此处async又来了一个
        engine = create_engine()    # 创建数据库引擎
        sm = create_session_maker(engine)   # 获得数据库连接
        storage = LocalFsStorage(root_dir=str(settings.blob_local_root))    # 创建本地文件存储对象
        qdrant = create_qdrant_client() # 创建qdrant客户端

        async with sm() as db:  # 传递给刚才的业务层, ingest_asset
            res = await ingest_asset(db=db, storage=storage, qdrant=qdrant, asset_id=int(asset_id))
            return {"ok": True, "asset_id": int(asset_id), "chunks": int(res.chunks), "points": int(res.points)}

    return asyncio.run(_run())  # 创建一个新的事件循环，执行异步_run()，等待完成，将结果作为task的返回值