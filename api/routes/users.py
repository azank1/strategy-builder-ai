"""User profile and subscription routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.database import get_db
from api.db_models import User
from api.schemas import UserProfile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_profile(user: User = Depends(get_current_user)) -> UserProfile:
    """Get the current user's profile and subscription info."""
    return UserProfile(
        id=user.id,
        wallet_address=user.wallet_address,
        ens_name=user.ens_name,
        tier=user.tier,
        subscription_expires_at=user.subscription_expires_at,
        allowed_assets=user.allowed_assets,
        created_at=user.created_at,
    )
