from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging_setup import setup_logging
from app.infra.db.engine import create_engine
from app.infra.db.session import create_session_maker
from app.infra.elasticsearch_client import create_es_client
from app.infra.qdrant_client import create_qdrant_client
from app.infra.blob_storage.local_fs import LocalFSStorage


class WorkerState:
    def __init__(self) -> None:  # 初始化运行一个celery的时候需要的各个组件，比如redis，es，db等等
        self.db_engine = create_engine()
        self.db_session_maker = create_session_maker(self.db_engine)
        self.redis = Redis.from_url(
            settings.redis_url,
            decode_responses=False,
            max_connections=settings.redis_max_connections,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_timeout=settings.redis_socket_timeout,
            retry_on_timeout=True,
            health_check_interval=settings.redis_health_check_interval,
        )
        self.es = create_es_client()
        self.qdrant = create_qdrant_client()
        self.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))


_state: WorkerState | None = None


def get_state() -> WorkerState:  # 返回上面这些组件的状态
    global _state
    if _state is None:
        setup_logging(level=settings.log_level)
        _state = WorkerState()
    return _state