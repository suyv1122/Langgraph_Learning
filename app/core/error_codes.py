from __future__ import annotations

# ERROR_MESSAGES：错误码影射去默认的message
ERROR_MESSAGES: dict[str, str] = {
    # 通用错误：校验失败
    "error.validation_failed": "validation_failed",

    # 通用错误：未捕获内部异常
    "error.internal": "internal_error",

    # 通用错误：HTTPException之类
    "error.http": "http_error",

    # 通用错误：触发限流
    "error.rate_limited": "rate_limited",

    # 鉴权：缺少bearer token
    "auth.bearer_required": "Missing bearer token",

    # 鉴权：access token无效（签名/格式/issuer等不对）
    "auth.access_token_invalid": "Invalid access token",

    # 鉴权：token版本过期/不一致
    "auth.access_token_expired": "Token expired",

    # 鉴权：用户不存在或禁用
    "auth.user_inactive": "User disabled or not found",

    # 注册：邮箱已存在
    "auth.email_taken": "Email already exists",

    # 登录：账号密码不对
    "auth.credentials_invalid": "Invalid credentials",

    # 刷新：refresh token无效
    "auth.refresh_token_invalid": "Invalid refresh token",

    # 刷新：refresh token已过期/被吊销/版本不匹配
    "auth.refresh_token_expired": "Refresh expired",

    # 授权：通用403 forbidden
    "rbac.forbidden": "forbidden",

    # 授权：没有任何角色
    "rbac.role_required": "no_role",

    # 授权：缺少某些权限
    "rbac.permission_missing": "missing_perms",

    # 管理：角色没找到
    "admin.role_not_found": "role not found",

    # 管理：用户没找到
    "admin.user_not_found": "user not found",

    # 存储：数据库错误
    "storage.db_error": "db_error",
}

# ERROR_STATUS：错误码 -> HTTP状态码
ERROR_STATUS: dict[str, int] = {
    # 校验失败：422
    "error.validation_failed": 422,

    # 内部错误：500
    "error.internal": 500,

    # 通用http错误：400
    "error.http": 400,

    # 限流：429
    "error.rate_limited": 429,

    # 缺token：401
    "auth.bearer_required": 401,

    # token无效：401
    "auth.access_token_invalid": 401,

    # token过期/版本不一致：401
    "auth.access_token_expired": 401,

    # 用户不可用：401
    "auth.user_inactive": 401,

    # 邮箱冲突：409
    "auth.email_taken": 409,

    # 凭证不对：401
    "auth.credentials_invalid": 401,

    # refresh无效：401
    "auth.refresh_token_invalid": 401,

    # refresh过期：401
    "auth.refresh_token_expired": 401,

    # 授权失败：403
    "rbac.forbidden": 403,

    # 无角色：403
    "rbac.role_required": 403,

    # 缺权限：403
    "rbac.permission_missing": 403,

    # 角色没找到：404
    "admin.role_not_found": 404,

    # 用户没找到：404
    "admin.user_not_found": 404,

    # DB错误：500
    "storage.db_error": 500,
}