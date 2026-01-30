from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

import importlib
import importlib.util

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.config import settings
from app.infra.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _import_models(dotted: str, fallback_relpath: str):
    try:
        return importlib.import_module(dotted)
    except Exception:
        path = os.path.join(BASE_DIR, fallback_relpath)
        spec = importlib.util.spec_from_file_location(dotted, path)
        if spec is None or spec.loader is None:
            raise
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

_audit_models = _import_models("app.modules.audit.models", "app/modules/audit/models.py")  # noqa: F401,E402
_auth_models = _import_models("app.modules.auth.models", "app/modules/auth/models.py")  # noqa: F401,E402
_resources_models = _import_models("app.modules.resources.models", "app/modules/resources/models.py")  # noqa: F401,E402


def run_migrations_offline() -> None:
    context.configure(
        url=str(settings.database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine = create_async_engine(
        str(settings.database_url),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())