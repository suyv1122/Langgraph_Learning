from __future__ import annotations
from typing import Optional

import uvicorn
from fastapi import APIRouter, Depends, HTTPException

from app.db import rbac_db
from app.model.rbac_model import SetUserRolesReq, SetRolePermsReq
from app.service.rbac_service import require_permission
from app.service.rbac_codes import Permission

# print("PERM:", Permission.PERM_SYSTEM_MANAGE_ROLES)
# print("TYPE:", type(Permission.PERM_SYSTEM_MANAGE_ROLES), getattr(Permission.PERM_SYSTEM_MANAGE_ROLES, "value", None))

router = APIRouter(prefix="/rbac", tags=["rbac"])

@router.get("/roles")
def api_list_roles(_: bool = Depends(require_permission(Permission.PERM_SYSTEM_MANAGE_ROLES))): # Depends 后接一个需求函数名(不需调用)，即此api需要满足需求函数后方可被调用
    return {"roles": rbac_db.list_roles()}

@router.get("/permissions")
def api_list_permissions(module: Optional[str] = None, _: bool = Depends(require_permission(Permission.PERM_SYSTEM_MANAGE_ROLES))):
    return {"permissions": rbac_db.list_permissions(module=module)}

@router.get("/roles/{role_code}/permissions")
def api_get_role_permissions(role_code: str, _: bool = Depends(require_permission(Permission.PERM_SYSTEM_MANAGE_ROLES))):
    return {"role": role_code, "permissions": rbac_db.get_role_permissions(role_code)}

@router.put("/roles/{role_code}/permissions")
def api_set_role_permissions(role_code: str, req: SetRolePermsReq, _: bool = Depends(require_permission(Permission.PERM_SYSTEM_MANAGE_ROLES))):
    try:
        rbac_db.set_role_permissions(role_code, req.perm_codes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "role": role_code, "permissions": rbac_db.get_role_permissions(role_code)}

@router.get("/users/{username}/roles")
def api_get_user_roles(username: str, _: bool = Depends(require_permission(Permission.PERM_SYSTEM_MANAGE_USERS))):
    uid = rbac_db.find_user_id(username)
    if uid is None:
        raise HTTPException(status_code=404, detail="user not found")
    return {"user": username, "user_id": uid, "roles": rbac_db.get_user_roles(uid)}

@router.put("/users/{username}/roles")
def api_set_user_roles(username: str, req: SetUserRolesReq, _: bool = Depends(require_permission(Permission.PERM_SYSTEM_MANAGE_USERS))):
    uid = rbac_db.find_user_id(username)
    if uid is None:
        raise HTTPException(status_code=404, detail="user not found")
    rbac_db.set_user_roles(uid, req.role_codes)
    return {"ok": True, "user": username, "user_id": uid, "roles": rbac_db.get_user_roles(uid)}

if __name__ == "__main__":
    uvicorn.run(router, host="0.0.0.0", port=8002, reload=True)