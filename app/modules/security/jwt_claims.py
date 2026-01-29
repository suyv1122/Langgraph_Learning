from __future__ import annotations

CLAIM_ISS = "iss"  # 签发者
CLAIM_SUB = "sub"  # JWT的标准字段subject，我们的项目里用作user_id
CLAIM_VER = "ver"  # token version
CLAIM_TYP = "typ"  # token类型，比如access or refresh
CLAIM_IAT = "iat"  # 签发时间
CLAIM_EXP = "exp"  # 过期时间

TOKEN_TYPE_ACCESS = "access"
