from __future__ import annotations

REFRESH_SEPARATOR = "."  # refresh token的分隔符

MAX_REFRESH_TOKEN_LEN = 4096
MAX_RID_LEN = 64  	# rid段最大长度，uuid实际是36，这里有多余的
MAX_SECRET_LEN = 256    # secret段最大长度

REDIS_PREFIX_REFRESH = "auth:refresh:"  	# redis key的前缀，这里是刷新令牌
REDIS_PREFIX_TOKENVER = "auth:tokenver:"  	# 也是redis key的前缀，这里是access token失效

RL_AUTH_REGISTER = "auth_register"  	# 注册限流
RL_AUTH_LOGIN = "auth_login"  		# 登录限流
RL_AUTH_REFRESH = "auth_refresh"  	# 刷新限流