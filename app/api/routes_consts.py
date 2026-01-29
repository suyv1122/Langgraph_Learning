NO_STORE_PATHS = {
    "/auth/login",
    "/auth/refresh", # 刷新令牌
    "/auth/logout",
    "/auth/me",
    "/auth/register",
    "/admin/grants", # 管理员为其他用户授权
}
# 这些路径所产生的信息不应被浏览器或任何其他中间键缓存