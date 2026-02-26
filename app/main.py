# TODO: 在application.state这类句子下方增加命令，正确性待校验
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.exception_handlers import install_exception_handlers
from app.api.health import router as health_router
from app.api.middleware.cors import install_cors
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.middleware.security_headers import SecurityHeadersMiddleware
from app.api.middleware.tenant import TenantContextMiddleware
from app.api.openapi import install_openapi
from app.api.startup_checks import run_startup_checks
from app.core.config import settings
from app.core.logging_setup import setup_logging
from app.infra.db.engine import create_engine
from app.infra.db.session import create_session_maker
from app.infra.elasticsearch_client import create_es_client
from app.modules.admin.routes import router as admin_router
from app.modules.authn.routes import router as auth_router
from app.modules.authz.seed_sync import sync_authz

from app.infra.qdrant_client import create_qdrant_client
from app.infra.blob_storage.local_fs import LocalFSStorage


@asynccontextmanager
async def lifespan(application: FastAPI):
    setup_logging(level=settings.log_level)

    engine = create_engine()
    application.state.db_engine = engine
    application.state.db_session_maker = create_session_maker(engine)
    application.state.qdrant = create_qdrant_client()
    application.state.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))

    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=False,
        max_connections=settings.redis_max_connections,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
        retry_on_timeout=True,
        health_check_interval=settings.redis_health_check_interval,
    )
    application.state.redis = redis
    application.state.qdrant = create_qdrant_client()
    application.state.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))

    application.state.es = create_es_client()
    application.state.qdrant = create_qdrant_client()
    application.state.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))

    await run_startup_checks(application)

    if settings.auto_sync_authz:
        async with application.state.db_session_maker() as db:
            application.state.qdrant = create_qdrant_client()
            application.state.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))
            await sync_authz(db)

    yield

    try:
        await application.state.es.close()
        application.state.qdrant = create_qdrant_client()
        application.state.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))
    except Exception:
        pass

    try:
        aclose = getattr(application.state.redis, "aclose", None)
        application.state.qdrant = create_qdrant_client()
        application.state.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))
        if callable(aclose):
            await aclose()
        else:
            await application.state.redis.close()
    except Exception:
        pass

    try:
        await application.state.db_engine.dispose()
        application.state.qdrant = create_qdrant_client()
        application.state.storage = LocalFSStorage(root_dir=str(settings.blob_local_root))
    except Exception:
        pass


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(TenantContextMiddleware)

install_exception_handlers(app)

install_cors(
    app,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods_list(),
    allow_headers=settings.cors_headers_list(),
)

if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware, content_security_policy=settings.csp)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_router)

install_openapi(app)
