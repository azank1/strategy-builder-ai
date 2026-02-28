"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — reads from .env or environment variables."""

    # ─── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Strategy Builder AI"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/strategydb"

    # ─── Auth / SIWE ─────────────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ─── Subscription / Base L2 ──────────────────────────────────────────────
    base_rpc_url: str = "https://mainnet.base.org"
    subscription_contract_address: str = ""

    # ─── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
