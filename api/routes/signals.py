"""Signal computation and retrieval routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_tier
from api.database import get_db
from api.db_models import IndicatorSystem, SignalSnapshot, SubscriptionTier, SystemType, User
from api.schemas import PortfolioResponse, SignalResponse

from strategy_engine.core.composite import CompositeScorer
from strategy_engine.models import (
    AssetClass,
    LTPISystem,
    SDCASystem,
)

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("/{system_id}/compute", response_model=SignalResponse)
async def compute_signal(
    system_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    """Re-compute the signal for a given system and store a snapshot."""
    system = await _get_system(db, user.id, system_id)

    scorer = CompositeScorer()
    signal_data: dict = {}
    snapshot_kwargs: dict = {"asset": system.asset}

    if system.system_type == SystemType.SDCA:
        sdca = SDCASystem(**system.system_data)
        result = scorer.score_sdca(sdca)
        snapshot_kwargs["sdca_composite_z"] = result.composite_z
        snapshot_kwargs["reasoning"] = result.interpretation
        signal_data = {"sdca": {"composite_z": result.composite_z, "interpretation": result.interpretation}}

    elif system.system_type == SystemType.LTPI:
        ltpi = LTPISystem(**system.system_data)
        result = scorer.score_ltpi(ltpi)
        snapshot_kwargs["ltpi_trend_ratio"] = result.trend_ratio
        snapshot_kwargs["reasoning"] = result.interpretation
        signal_data = {"ltpi": {"trend_ratio": result.trend_ratio, "interpretation": result.interpretation}}

    snapshot = SignalSnapshot(
        user_id=user.id,
        system_id=system.id,
        signal_data=signal_data,
        **snapshot_kwargs,
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)
    return SignalResponse.model_validate(snapshot)


@router.get("/{system_id}/latest", response_model=SignalResponse)
async def get_latest_signal(
    system_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    """Get the most recent computed signal for a system."""
    result = await db.execute(
        select(SignalSnapshot)
        .where(
            SignalSnapshot.system_id == system_id,
            SignalSnapshot.user_id == user.id,
        )
        .order_by(SignalSnapshot.computed_at.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No signals computed yet — call POST /compute first",
        )
    return SignalResponse.model_validate(snapshot)


@router.get("/{system_id}/history", response_model=list[SignalResponse])
async def get_signal_history(
    system_id: uuid.UUID,
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SignalResponse]:
    """Get signal history for a system (newest first)."""
    result = await db.execute(
        select(SignalSnapshot)
        .where(
            SignalSnapshot.system_id == system_id,
            SignalSnapshot.user_id == user.id,
        )
        .order_by(SignalSnapshot.computed_at.desc())
        .limit(min(limit, 100))
    )
    snapshots = result.scalars().all()
    return [SignalResponse.model_validate(s) for s in snapshots]


@router.post("/portfolio", response_model=PortfolioResponse)
async def compute_portfolio(
    user: User = Depends(require_tier(SubscriptionTier.STRATEGIST)),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """Compute a combined portfolio signal across all active systems.

    Requires Strategist tier or above.
    """
    result = await db.execute(
        select(IndicatorSystem).where(
            IndicatorSystem.user_id == user.id,
            IndicatorSystem.is_active == True,  # noqa: E712
        )
    )
    systems = result.scalars().all()
    if not systems:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active systems found — create systems first",
        )

    scorer = CompositeScorer()
    signals: list[SignalResponse] = []

    # Group systems by asset for combined scoring
    for system in systems:
        signal_data: dict = {}
        snapshot_kwargs: dict = {"asset": system.asset}

        if system.system_type == SystemType.SDCA:
            sdca = SDCASystem(**system.system_data)
            r = scorer.score_sdca(sdca)
            snapshot_kwargs["sdca_composite_z"] = r.composite_z
            snapshot_kwargs["reasoning"] = r.interpretation
            signal_data = {"sdca": {"composite_z": r.composite_z}}
        elif system.system_type == SystemType.LTPI:
            ltpi = LTPISystem(**system.system_data)
            r = scorer.score_ltpi(ltpi)
            snapshot_kwargs["ltpi_trend_ratio"] = r.trend_ratio
            snapshot_kwargs["reasoning"] = r.interpretation
            signal_data = {"ltpi": {"trend_ratio": r.trend_ratio}}

        snapshot = SignalSnapshot(
            user_id=user.id,
            system_id=system.id,
            signal_data=signal_data,
            **snapshot_kwargs,
        )
        db.add(snapshot)
        await db.flush()
        await db.refresh(snapshot)
        signals.append(SignalResponse.model_validate(snapshot))

    total_alloc = sum(s.allocation_pct or 0.0 for s in signals)
    return PortfolioResponse(
        signals=signals,
        total_allocation=total_alloc,
        computed_at=datetime.now(timezone.utc),
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _get_system(
    db: AsyncSession, user_id: uuid.UUID, system_id: uuid.UUID
) -> IndicatorSystem:
    result = await db.execute(
        select(IndicatorSystem).where(
            IndicatorSystem.id == system_id,
            IndicatorSystem.user_id == user_id,
        )
    )
    system = result.scalar_one_or_none()
    if system is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System not found")
    return system
