# 7.6
from __future__ import annotations

from typing import Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.deps import get_db
from app.modules.auth.models import User
from app.modules.authn.deps import get_current_user
from app.modules.authz.service import require_perms

def permission_required(*perm_codes: str, scope_builder: Callable[[Request], str]):
    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        scope_key = str(scope_builder(request))  # 用scope_builder根据request动态生成scope_key
        await require_perms(db, user=user, scope_key=scope_key, perm_codes=list(perm_codes)) # 调用RBAC核心校验逻辑，不通过抛AppError
        return user  # 通过则把用户返回给路由函数

    return _dep  # 返回可用于Depends(...)的依赖函数
