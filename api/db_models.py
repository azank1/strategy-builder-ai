"""SQLAlchemy database models for the API layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# ─── Enums ────────────────────────────────────────────────────────────────────


class SubscriptionTier(str, PyEnum):
    EXPLORER = "explorer"       # Free  — BTC only
    STRATEGIST = "strategist"   # ~$29  — BTC + ETH + Gold + SPX
    QUANT = "quant"             # ~$99  — All assets + alt rotation + ML insights


class SystemType(str, PyEnum):
    SDCA = "sdca"
    LTPI = "ltpi"


# ─── Users & Auth ─────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    wallet_address: Mapped[str] = mapped_column(
        String(42), unique=True, nullable=False, index=True,
        comment="Ethereum-compatible wallet address (0x...)"
    )
    ens_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.EXPLORER, nullable=False
    )
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    systems: Mapped[list["IndicatorSystem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    signals: Mapped[list["SignalSnapshot"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def is_subscription_active(self) -> bool:
        if self.tier == SubscriptionTier.EXPLORER:
            return True  # free tier always active
        if self.subscription_expires_at is None:
            return False
        return self.subscription_expires_at > datetime.now(timezone.utc)

    @property
    def allowed_assets(self) -> list[str]:
        match self.tier:
            case SubscriptionTier.EXPLORER:
                return ["btc"]
            case SubscriptionTier.STRATEGIST:
                return ["btc", "eth", "gold", "spx"]
            case SubscriptionTier.QUANT:
                return ["btc", "eth", "gold", "spx", "alt"]


# ─── Indicator Systems ───────────────────────────────────────────────────────


class IndicatorSystem(Base):
    __tablename__ = "indicator_systems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    system_type: Mapped[SystemType] = mapped_column(
        Enum(SystemType), nullable=False
    )
    asset: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full system data stored as JSON (Pydantic models serialised)
    system_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="systems")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_system_name"),
    )


# ─── Signal Snapshots ────────────────────────────────────────────────────────


class SignalSnapshot(Base):
    """Periodic snapshot of a computed signal for a user's system."""

    __tablename__ = "signal_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("indicator_systems.id"), nullable=False, index=True
    )
    asset: Mapped[str] = mapped_column(String(10), nullable=False)

    # Signal results
    sdca_composite_z: Mapped[float | None] = mapped_column(Float, nullable=True)
    ltpi_trend_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_strength: Mapped[str | None] = mapped_column(String(30), nullable=True)
    allocation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full payload
    signal_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="signals")
