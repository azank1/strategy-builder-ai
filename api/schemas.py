"""Pydantic schemas for API request/response bodies."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from api.db_models import SubscriptionTier, SystemType


# ─── Auth ─────────────────────────────────────────────────────────────────────


class SIWERequest(BaseModel):
    """Sign-In with Ethereum request payload."""
    message: str = Field(..., description="Full SIWE message string")
    signature: str = Field(..., description="Hex-encoded signature (0x...)")


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    wallet_address: str
    tier: SubscriptionTier
    expires_in: int = Field(..., description="Token lifetime in seconds")


class NonceResponse(BaseModel):
    nonce: str


# ─── User ─────────────────────────────────────────────────────────────────────


class UserProfile(BaseModel):
    id: uuid.UUID
    wallet_address: str
    ens_name: Optional[str] = None
    tier: SubscriptionTier
    subscription_expires_at: Optional[datetime] = None
    allowed_assets: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Systems ─────────────────────────────────────────────────────────────────


class SystemCreateRequest(BaseModel):
    system_type: SystemType
    asset: str = Field(..., pattern="^(btc|eth|gold|spx|alt)$")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_data: dict = Field(..., description="Full Pydantic model serialized as JSON")


class SystemUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    system_data: Optional[dict] = None
    is_active: Optional[bool] = None


class SystemResponse(BaseModel):
    id: uuid.UUID
    system_type: SystemType
    asset: str
    name: str
    description: Optional[str]
    system_data: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Signals ─────────────────────────────────────────────────────────────────


class SignalResponse(BaseModel):
    id: uuid.UUID
    asset: str
    sdca_composite_z: Optional[float]
    ltpi_trend_ratio: Optional[float]
    signal_strength: Optional[str]
    allocation_pct: Optional[float]
    reasoning: Optional[str]
    computed_at: datetime

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    """Multi-asset portfolio signal."""
    signals: list[SignalResponse]
    total_allocation: float = Field(..., description="Sum of allocation_pct (should be ~1.0)")
    computed_at: datetime


# ─── Health ───────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
