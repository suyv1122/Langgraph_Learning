# 1.2
from enum import Enum

class Env(str, Enum):  		# 定义这个东西主要是开发、生产与发布
    dev = "dev"  		# 开发环境：本地开发、调试
    prod = "prod" 		# 生产环境
    production = "production" 	# 生产环境，这里防止有人写全称，留一个也可以其实
    staging = "staging"  	# 预发布/测试环境：介于开发和生产环境之间

class JwtAlg(str, Enum):  	# 这个主要搞签名算法的枚举
    HS256 = "HS256"  		# 对称密钥算法：用同一把secret做签名与验签
    RS256 = "RS256"  		# 非对称密钥算法：用私钥签名、公钥验签（你当前实现主要用 HS256）