"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — reads from .env or environment variables."""

    # ─── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Strategy Builder AI"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/strategydb"

    # ─── Redis (optional — needed for nonce store in production) ──────────────
    redis_url: str = ""

    # ─── Auth / SIWE ─────────────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ─── Subscription / Base L2 ──────────────────────────────────────────────
    base_rpc_url: str = "https://mainnet.base.org"
    subscription_contract_address: str = ""

    # ─── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]

    # ─── Admin ────────────────────────────────────────────────────────────────
    admin_wallets: list[str] = []  # lowercase wallet addresses with admin access

    @model_validator(mode="after")
    def _validate_production_secrets(self):
        if self.environment == "production":
            if self.jwt_secret_key == "CHANGE-ME-IN-PRODUCTION":
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a real secret in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            if not self.redis_url:
                raise ValueError("REDIS_URL must be set in production for nonce storage")
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
