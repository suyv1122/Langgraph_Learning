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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    qdrant_url: str = Field(default="http://127.0.0.1:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_timeout_seconds: float = Field(default=10.0, alias="QDRANT_TIMEOUT_SECONDS")
    qdrant_collection: str = Field(default="kb_chunks", alias="QDRANT_COLLECTION")

    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")

    blob_backend: str = Field(default="local", alias="BLOB_BACKEND")
    blob_local_root: str = Field(default="./data/blob", alias="BLOB_LOCAL_ROOT")

    blob_s3_endpoint_url: str | None = Field(default=None, alias="BLOB_S3_ENDPOINT_URL")
    blob_s3_bucket: str | None = Field(default=None, alias="BLOB_S3_BUCKET")
    blob_s3_access_key_id: str | None = Field(default=None, alias="BLOB_S3_ACCESS_KEY_ID")
    blob_s3_secret_access_key: str | None = Field(default=None, alias="BLOB_S3_SECRET_ACCESS_KEY")
    blob_s3_region: str | None = Field(default=None, alias="BLOB_S3_REGION")

    kb_chunk_max_chars: int = Field(default=1200, alias="KB_CHUNK_MAX_CHARS")
    kb_chunk_overlap_chars: int = Field(default=120, alias="KB_CHUNK_OVERLAP_CHARS")
    kb_bm25_max_docs: int = Field(default=2000, alias="KB_BM25_MAX_DOCS")

    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        if (self.cors_allow_origins or "").strip() == "*" and bool(self.cors_allow_credentials):
            raise ValueError("CORS_ALLOW_CREDENTIALS cannot be true when CORS_ALLOW_ORIGINS is '*'.")
        return self

    @staticmethod
    def _csv(s: str) -> list[str]:
        s = (s or "").strip()
        if not s:
            return []
        return [x.strip() for x in s.split(",") if x.strip()]

    def cors_origins_list(self) -> list[str]:
        if (self.cors_allow_origins or "").strip() == "*":
            return ["*"]
        return self._csv(self.cors_allow_origins)

    def cors_methods_list(self) -> list[str]:
        return self._csv(self.cors_allow_methods) or ["*"]

    def cors_headers_list(self) -> list[str]:
        return self._csv(self.cors_allow_headers) or ["*"]

    @model_validator(mode="after")
    def _validate_blob_backend(self) -> "Settings":
        backend = (self.blob_backend or "").strip().lower()
        if backend not in {"local", "s3"}:
            raise ValueError("BLOB_BACKEND must be either 'local' or 's3'.")
        if backend == "s3":
            missing = []
            if not self.blob_s3_bucket:
                missing.append("BLOB_S3_BUCKET")
            if not self.blob_s3_access_key_id:
                missing.append("BLOB_S3_ACCESS_KEY_ID")
            if not self.blob_s3_secret_access_key:
                missing.append("BLOB_S3_SECRET_ACCESS_KEY")
            if missing:
                raise ValueError(f"S3 blob backend enabled but missing required settings: {', '.join(missing)}")
        return self

    @model_validator(mode="after")
    def _validate_kb_chunking(self) -> "Settings":
        if self.kb_chunk_max_chars <= 0:
            raise ValueError("KB_CHUNK_MAX_CHARS must be > 0.")
        if self.kb_chunk_overlap_chars < 0:
            raise ValueError("KB_CHUNK_OVERLAP_CHARS must be >= 0.")
        if self.kb_chunk_overlap_chars >= self.kb_chunk_max_chars:
            raise ValueError("KB_CHUNK_OVERLAP_CHARS must be smaller than KB_CHUNK_MAX_CHARS.")
        if self.kb_bm25_max_docs <= 0:
            raise ValueError("KB_BM25_MAX_DOCS must be > 0.")
        if self.qdrant_timeout_seconds <= 0:
            raise ValueError("QDRANT_TIMEOUT_SECONDS must be > 0.")
        return self


settings = Settings()