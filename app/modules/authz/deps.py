from __future__ import annotations

from typing import Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.deps import get_db
from app.modules.auth.models import User
from app.modules.authn.deps import get_current_user
from app.modules.authz.service import require_any_perms, require_perms


def permission_required(*perm_codes: str, scope_builder: Callable[[Request], str]):
    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        scope_key = str(scope_builder(request))
        await require_perms(db, user=user, scope_key=scope_key, perm_codes=list(perm_codes))
        return user

    return _dep


def any_permission_required(*perm_codes: str, scope_builder: Callable[[Request], str]):
    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        scope_key = str(scope_builder(request))
        await require_any_perms(db, user=user, scope_key=scope_key, perm_codes=list(perm_codes))
        return user

    return _dep