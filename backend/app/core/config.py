"""MEMBRA CompanyOS — Production Configuration."""
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Pydantic settings with env-file support and validation."""

    # App Identity
    app_name: str = Field(default="MEMBRA CompanyOS", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    # Security
    secret_key: str = Field(default="change-me-in-production-32-char-safe", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/membracos",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/membracos",
        alias="DATABASE_URL_SYNC",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", alias="CELERY_RESULT_BACKEND")

    # LLM Providers (optional — graceful degradation)
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    default_llm_provider: str = Field(default="groq", alias="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field(default="llama-3.3-70b-versatile", alias="DEFAULT_LLM_MODEL")

    # Settlement / Blockchain (optional)
    solana_rpc_url: Optional[str] = Field(default=None, alias="SOLANA_RPC_URL")
    ethereum_rpc_url: Optional[str] = Field(default=None, alias="ETHEREUM_RPC_URL")
    settlement_webhook_url: Optional[str] = Field(default=None, alias="SETTLEMENT_WEBHOOK_URL")

    # IPFS / ProofBook (optional)
    pinata_api_key: Optional[str] = Field(default=None, alias="PINATA_API_KEY")
    pinata_secret: Optional[str] = Field(default=None, alias="PINATA_SECRET")

    # Rate Limiting
    rate_limit_auth: str = Field(default="5/minute", alias="RATE_LIMIT_AUTH")
    rate_limit_api: str = Field(default="100/minute", alias="RATE_LIMIT_API")

    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # Governance
    admin_wallets: str = Field(default="", alias="ADMIN_WALLETS")
    require_governance_approval: bool = Field(default=True, alias="REQUIRE_GOVERNANCE_APPROVAL")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters")
        return v

    @property
    def admin_wallet_list(self) -> List[str]:
        return [w.strip().lower() for w in self.admin_wallets.split(",") if w.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton
settings = Settings()
