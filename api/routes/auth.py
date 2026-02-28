"""Authentication routes — SIWE login flow."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import (
    create_access_token,
    generate_nonce,
    get_or_create_user,
    verify_siwe_message,
)
from api.database import get_db
from api.schemas import AuthResponse, NonceResponse, SIWERequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/nonce", response_model=NonceResponse)
async def get_nonce() -> NonceResponse:
    """Generate a one-time nonce for SIWE message construction."""
    return NonceResponse(nonce=generate_nonce())


@router.post("/login", response_model=AuthResponse)
async def login(body: SIWERequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Verify a SIWE signature and return a JWT."""
    wallet_address = verify_siwe_message(body.message, body.signature)
    user = await get_or_create_user(db, wallet_address)
    token, expires_in = create_access_token(user.wallet_address, user.id)
    return AuthResponse(
        access_token=token,
        wallet_address=user.wallet_address,
        tier=user.tier,
        expires_in=expires_in,
    )
