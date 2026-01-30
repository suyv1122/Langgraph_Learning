# 1.10
DEFAULT_HSTS_MAX_AGE = 31536000
# HSTS的默认max-age此处是秒，一共是365天
# 浏览器在接下来1年内访问这个域名时都会强制使用HTTPS

DEFAULT_X_FRAME_OPTIONS = "DENY"
# X-Frame-Options默认值DENY表示不允许页面被嵌入iframe，这里主要是防点击劫持

DEFAULT_REFERRER_POLICY = "no-referrer"
# Referrer-Policy默认值不发送referrer，减少泄露来源

DEFAULT_PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=()"
# Permissions-Policy默认值禁止地理位置/麦克风/摄像头权限，此处的()表示不允许任何来源