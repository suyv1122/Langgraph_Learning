from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import Env, JwtAlg
from app.core.security_defaults import (
    DEFAULT_HSTS_MAX_AGE,
    DEFAULT_PERMISSIONS_POLICY,
    DEFAULT_REFERRER_POLICY,
    DEFAULT_X_FRAME_OPTIONS,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/Users/peter/PycharmProjects/enterprise-assistant/.env",
                                      env_file_encoding="utf-8")

    env: Env = Field(default=Env.dev, alias="ENV")

    app_name: str = Field(default="enterprise-assistant", alias="APP_NAME")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(..., alias="DATABASE_URL")

    redis_url: str = Field(..., alias="REDIS_URL")

    rabbitmq_url: str = Field(..., alias="RABBITMQ_URL")

    celery_result_backend: str = Field(default="redis://127.0.0.1:6379/1", alias="CELERY_RESULT_BACKEND")

    celery_task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")

    elasticsearch_url: str = Field(default="http://127.0.0.1:9200", alias="ELASTICSEARCH_URL")

    elasticsearch_username: str | None = Field(default=None, alias="ELASTICSEARCH_USERNAME")

    elasticsearch_password: str | None = Field(default=None, alias="ELASTICSEARCH_PASSWORD")

    elasticsearch_verify_certs: bool = Field(default=False, alias="ELASTICSEARCH_VERIFY_CERTS")

    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")

    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")

    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")

    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")

    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")

    redis_socket_connect_timeout: int = Field(default=2, alias="REDIS_SOCKET_CONNECT_TIMEOUT")

    redis_socket_timeout: int = Field(default=2, alias="REDIS_SOCKET_TIMEOUT")

    redis_health_check_interval: int = Field(default=30, alias="REDIS_HEALTH_CHECK_INTERVAL")

    jwt_secret: str = Field(..., alias="JWT_SECRET")

    jwt_issuer: str = Field(default="enterprise-assistant", alias="JWT_ISSUER")

    jwt_alg: JwtAlg = Field(default=JwtAlg.HS256, alias="JWT_ALG")

    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    auto_sync_authz: bool = Field(default=True, alias="AUTO_SYNC_AUTHZ")

    security_headers_enabled: bool = Field(default=True, alias="SECURITY_HEADERS_ENABLED")

    csp: str | None = Field(default=None, alias="CSP")

    security_hsts_enabled: bool = Field(default=False, alias="SECURITY_HSTS_ENABLED")

    security_hsts_max_age: int = Field(default=DEFAULT_HSTS_MAX_AGE, alias="SECURITY_HSTS_MAX_AGE")

    security_hsts_include_subdomains: bool = Field(default=True, alias="SECURITY_HSTS_INCLUDE_SUBDOMAINS")

    security_hsts_preload: bool = Field(default=False, alias="SECURITY_HSTS_PRELOAD")

    security_x_frame_options: str = Field(default=DEFAULT_X_FRAME_OPTIONS, alias="SECURITY_X_FRAME_OPTIONS")

    security_referrer_policy: str = Field(default=DEFAULT_REFERRER_POLICY, alias="SECURITY_REFERRER_POLICY")

    security_permissions_policy: str = Field(default=DEFAULT_PERMISSIONS_POLICY, alias="SECURITY_PERMISSIONS_POLICY")

    cors_allow_origins: str = Field(default="*", alias="CORS_ALLOW_ORIGINS")

    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")

    cors_allow_methods: str = Field(default="GET,POST,PUT,PATCH,DELETE,OPTIONS", alias="CORS_ALLOW_METHODS")

    cors_allow_headers: str = Field(default="Authorization,Content-Type,X-Request-Id", alias="CORS_ALLOW_HEADERS")

    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")

    auth_rate_limit_per_window: int = Field(default=20, alias="AUTH_RATE_LIMIT_PER_WINDOW")

    auth_rate_limit_window_seconds: int = Field(default=60, alias="AUTH_RATE_LIMIT_WINDOW_SECONDS")

    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        if (self.cors_allow_origins or "").strip() == "*" and bool(self.cors_allow_credentials):
            # 当allow_origins是*时，规范上不允许allow_credentials为true，浏览器会拒绝
            # 这里用校验器强制阻止这种组合配置

            raise ValueError("CORS_ALLOW_CREDENTIALS cannot be true when CORS_ALLOW_ORIGINS is '*'.")
            # 抛ValueError会让Settings初始化失败，从而在启动时暴露配置错误

        return self
        # 校验通过返回self，这里为啥要返回self主要是因为Pydantic v2 after-validator的惯例

    @staticmethod
    def _csv(s: str) -> list[str]:
        s = (s or "").strip()
        if not s:
            return []
        return [x.strip() for x in s.split(",") if x.strip()]

    def cors_origins_list(self) -> list[str]:
        if (self.cors_allow_origins or "").strip() == "*":
            # 如果配置是*就直接返回 ["*"]表示允许任意来源）
            return ["*"]  # 这里为什么用列表，主要是要统一输出给middleware
        return self._csv(self.cors_allow_origins)  # 否则按CSV规则分割成列表

    def cors_methods_list(self) -> list[str]:  # 允许POST，GET等这种方法
        return self._csv(self.cors_allow_methods) or ["*"]
        # 分割methods；如果最终为空则回退为["*"]表示允许所有方法

    def cors_headers_list(self) -> list[str]:  # 运行请求头字段中的内容
        return self._csv(self.cors_allow_headers) or ["*"]
        # 分割headers；如果最终为空则回退为 ["*"]表示允许所有头


settings = Settings()