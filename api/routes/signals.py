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


# ─── Dashboard summary ────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=list[SignalResponse])
async def dashboard_signals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SignalResponse]:
    """Return the latest signal for every active system (avoids N+1)."""
    # Get all active system IDs
    sys_result = await db.execute(
        select(IndicatorSystem.id).where(
            IndicatorSystem.user_id == user.id,
            IndicatorSystem.is_active == True,  # noqa: E712
        )
    )
    system_ids = [row[0] for row in sys_result.all()]
    if not system_ids:
        return []

    # For each system, fetch the latest snapshot
    signals: list[SignalResponse] = []
    for sid in system_ids:
        result = await db.execute(
            select(SignalSnapshot)
            .where(
                SignalSnapshot.system_id == sid,
                SignalSnapshot.user_id == user.id,
            )
            .order_by(SignalSnapshot.computed_at.desc())
            .limit(1)
        )
        snap = result.scalar_one_or_none()
        if snap is not None:
            signals.append(SignalResponse.model_validate(snap))

    return signals


# ─── Internal mapping: public system types → engine types ─────────────────────

_ENGINE_MAP = {
    SystemType.VALUATION: ("sdca", SDCASystem, "score_sdca"),
    SystemType.TREND: ("trend", LTPISystem, "score_ltpi"),
    # SystemType.MOMENTUM: ("momentum", ..., "score_mtpi"),  # future
    # SystemType.ROTATION: ("rotation", ..., "score_rotation"),  # future
}


def _compute_for_system(
    scorer: CompositeScorer, system: IndicatorSystem
) -> tuple[dict, dict]:
    """Run engine computation; returns (snapshot_kwargs, signal_data)."""
    mapping = _ENGINE_MAP.get(system.system_type)
    if mapping is None:
        return {"asset": system.asset}, {}

    _key, model_cls, scorer_method = mapping
    engine_obj = model_cls(**system.system_data)
    result = getattr(scorer, scorer_method)(engine_obj)

    snapshot_kwargs: dict = {"asset": system.asset}
    signal_data: dict = {}

    if system.system_type == SystemType.VALUATION:
        snapshot_kwargs["valuation_score"] = result.composite_z
        snapshot_kwargs["reasoning"] = result.interpretation
        signal_data = {"valuation": {"score": result.composite_z, "interpretation": result.interpretation}}
    elif system.system_type == SystemType.TREND:
        snapshot_kwargs["trend_score"] = result.trend_ratio
        snapshot_kwargs["reasoning"] = result.interpretation
        signal_data = {"trend": {"score": result.trend_ratio, "interpretation": result.interpretation}}

    return snapshot_kwargs, signal_data


@router.post("/{system_id}/compute", response_model=SignalResponse)
async def compute_signal(
    system_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    """Re-compute the signal for a given system and store a snapshot."""
    system = await _get_system(db, user.id, system_id)
    scorer = CompositeScorer()
    snapshot_kwargs, signal_data = _compute_for_system(scorer, system)

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

    for system in systems:
        snapshot_kwargs, signal_data = _compute_for_system(scorer, system)

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
