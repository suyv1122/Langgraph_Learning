# 2.4
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_context import get_workspace_id


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_maker = request.app.state.db_session_maker
    async with session_maker() as session:
        wid = getattr(request.state, "workspace_id", None)
        if wid is None:
            wid = get_workspace_id()
        wid_val = str(int(wid)) if wid is not None else "0"
        await session.execute(text("SELECT set_config('app.tenant_id', :v, true)"), {"v": wid_val})
        yield session