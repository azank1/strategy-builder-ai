"""System CRUD routes — create, read, update, delete indicator systems."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.database import get_db
from api.db_models import IndicatorSystem, User
from api.schemas import SystemCreateRequest, SystemResponse, SystemUpdateRequest

router = APIRouter(prefix="/systems", tags=["systems"])


def _check_asset_access(user: User, asset: str) -> None:
    """Raise 403 if the user's tier doesn't cover this asset."""
    if asset not in user.allowed_assets:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Asset '{asset}' requires a higher subscription tier",
        )


@router.get("/", response_model=list[SystemResponse])
async def list_systems(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SystemResponse]:
    """List all indicator systems for the current user."""
    result = await db.execute(
        select(IndicatorSystem)
        .where(IndicatorSystem.user_id == user.id)
        .order_by(IndicatorSystem.created_at.desc())
    )
    systems = result.scalars().all()
    return [SystemResponse.model_validate(s) for s in systems]


@router.post("/", response_model=SystemResponse, status_code=status.HTTP_201_CREATED)
async def create_system(
    body: SystemCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SystemResponse:
    """Create a new indicator system."""
    _check_asset_access(user, body.asset)

    system = IndicatorSystem(
        user_id=user.id,
        system_type=body.system_type,
        asset=body.asset,
        name=body.name,
        description=body.description,
        system_data=body.system_data,
    )
    db.add(system)
    await db.flush()
    await db.refresh(system)
    return SystemResponse.model_validate(system)


@router.get("/{system_id}", response_model=SystemResponse)
async def get_system(
    system_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SystemResponse:
    """Get a single system by ID."""
    system = await _get_user_system(db, user.id, system_id)
    return SystemResponse.model_validate(system)


@router.patch("/{system_id}", response_model=SystemResponse)
async def update_system(
    system_id: uuid.UUID,
    body: SystemUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SystemResponse:
    """Update an existing system."""
    system = await _get_user_system(db, user.id, system_id)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(system, key, value)

    await db.flush()
    await db.refresh(system)
    return SystemResponse.model_validate(system)


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system(
    system_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a system."""
    system = await _get_user_system(db, user.id, system_id)
    await db.delete(system)


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _get_user_system(
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
