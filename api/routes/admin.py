"""Admin routes — gated behind wallet allowlist."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_admin
from api.database import get_db
from api.db_models import (
    IndicatorSystem,
    SignalSnapshot,
    SubscriptionTier,
    User,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class AdminUserRow(BaseModel):
    id: uuid.UUID
    wallet_address: str
    ens_name: Optional[str] = None
    tier: SubscriptionTier
    subscription_expires_at: Optional[datetime] = None
    system_count: int = 0
    signal_count: int = 0
    created_at: datetime


class AdminUsersResponse(BaseModel):
    users: list[AdminUserRow]
    total: int
    page: int
    page_size: int


class TierUpdateRequest(BaseModel):
    tier: SubscriptionTier
    subscription_expires_at: Optional[datetime] = None


class PlatformStats(BaseModel):
    total_users: int = 0
    users_by_tier: dict[str, int] = Field(default_factory=dict)
    total_systems: int = 0
    total_signals: int = 0
    signals_last_24h: int = 0


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tier: Optional[SubscriptionTier] = None,
    search: Optional[str] = None,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUsersResponse:
    """List all users (paginated). Filterable by tier or wallet search."""
    q = select(User)
    count_q = select(func.count(User.id))

    if tier is not None:
        q = q.where(User.tier == tier)
        count_q = count_q.where(User.tier == tier)
    if search:
        q = q.where(User.wallet_address.ilike(f"%{search}%"))
        count_q = count_q.where(User.wallet_address.ilike(f"%{search}%"))

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        q.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    rows: list[AdminUserRow] = []
    for u in users:
        sys_count = (
            await db.execute(
                select(func.count(IndicatorSystem.id)).where(
                    IndicatorSystem.user_id == u.id
                )
            )
        ).scalar() or 0
        sig_count = (
            await db.execute(
                select(func.count(SignalSnapshot.id)).where(
                    SignalSnapshot.user_id == u.id
                )
            )
        ).scalar() or 0
        rows.append(
            AdminUserRow(
                id=u.id,
                wallet_address=u.wallet_address,
                ens_name=u.ens_name,
                tier=u.tier,
                subscription_expires_at=u.subscription_expires_at,
                system_count=sys_count,
                signal_count=sig_count,
                created_at=u.created_at,
            )
        )

    return AdminUsersResponse(
        users=rows, total=total, page=page, page_size=page_size
    )


@router.patch("/users/{user_id}/tier")
async def update_user_tier(
    user_id: uuid.UUID,
    body: TierUpdateRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manually set a user's tier (support / overrides)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.tier = body.tier
    if body.subscription_expires_at is not None:
        user.subscription_expires_at = body.subscription_expires_at
    await db.flush()
    return {"ok": True, "tier": user.tier.value}


@router.get("/stats", response_model=PlatformStats)
async def platform_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformStats:
    """Platform-level metrics."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # Tier breakdown
    tier_rows = (
        await db.execute(
            select(User.tier, func.count(User.id)).group_by(User.tier)
        )
    ).all()
    users_by_tier = {str(row[0].value): row[1] for row in tier_rows}

    total_systems = (
        await db.execute(select(func.count(IndicatorSystem.id)))
    ).scalar() or 0

    total_signals = (
        await db.execute(select(func.count(SignalSnapshot.id)))
    ).scalar() or 0

    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    signals_24h = (
        await db.execute(
            select(func.count(SignalSnapshot.id)).where(
                SignalSnapshot.computed_at >= cutoff
            )
        )
    ).scalar() or 0

    return PlatformStats(
        total_users=total_users,
        users_by_tier=users_by_tier,
        total_systems=total_systems,
        total_signals=total_signals,
        signals_last_24h=signals_24h,
    )
