"""Authentication — SIWE (Sign-In with Ethereum) + JWT."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from siwe import SiweMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_db
from api.db_models import SubscriptionTier, User

logger = logging.getLogger(__name__)

_settings = get_settings()
_bearer = HTTPBearer()

# ─── Nonce store ─────────────────────────────────────────────────────────────
# Uses Redis when REDIS_URL is configured; falls back to in-memory for dev.

_redis_client = None
_fallback_nonces: dict[str, datetime] = {}
_NONCE_TTL = 600  # 10 minutes


def _get_redis():
    """Lazily initialise a Redis client if configured."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if _settings.redis_url:
        try:
            import redis
            _redis_client = redis.from_url(
                _settings.redis_url, decode_responses=True
            )
            _redis_client.ping()
            logger.info("Nonce store: Redis")
            return _redis_client
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — falling back to in-memory nonces", exc)
            _redis_client = False  # sentinel: don't retry
    return None


def generate_nonce() -> str:
    """Generate a cryptographic nonce for SIWE."""
    nonce = secrets.token_hex(16)
    r = _get_redis()
    if r:
        r.setex(f"siwe:nonce:{nonce}", _NONCE_TTL, "1")
    else:
        _fallback_nonces[nonce] = datetime.now(timezone.utc) + timedelta(seconds=_NONCE_TTL)
        # Prune expired nonces
        now = datetime.now(timezone.utc)
        expired = [k for k, v in _fallback_nonces.items() if v < now]
        for k in expired:
            _fallback_nonces.pop(k, None)
    return nonce


def verify_nonce(nonce: str) -> bool:
    """Verify and consume a nonce (single-use)."""
    r = _get_redis()
    if r:
        return bool(r.delete(f"siwe:nonce:{nonce}"))
    expiry = _fallback_nonces.pop(nonce, None)
    if expiry is None:
        return False
    return expiry > datetime.now(timezone.utc)


def verify_siwe_message(message: str, signature: str) -> str:
    """Verify a SIWE message+signature. Returns the wallet address."""
    try:
        siwe_msg = SiweMessage.from_message(message=message)
        siwe_msg.verify(signature=signature)
        if not verify_nonce(siwe_msg.nonce):
            raise ValueError("Invalid or expired nonce")
        return siwe_msg.address
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"SIWE verification failed: {e}",
        )


def create_access_token(wallet_address: str, user_id: uuid.UUID) -> tuple[str, int]:
    """Create a JWT. Returns (token, expires_in_seconds)."""
    expires_delta = timedelta(minutes=_settings.jwt_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": wallet_address,
        "uid": str(user_id),
        "exp": expire,
    }
    token = jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


async def get_or_create_user(db: AsyncSession, wallet_address: str) -> User:
    """Find an existing user by wallet or create a new Explorer-tier account."""
    result = await db.execute(
        select(User).where(User.wallet_address == wallet_address.lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            wallet_address=wallet_address.lower(),
            tier=SubscriptionTier.EXPLORER,
        )
        db.add(user)
        await db.flush()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — decode JWT and return the User row."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            _settings.jwt_secret_key,
            algorithms=[_settings.jwt_algorithm],
        )
        wallet: Optional[str] = payload.get("sub")
        if wallet is None:
            raise JWTError("Missing subject")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(User).where(User.wallet_address == wallet.lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_tier(minimum: SubscriptionTier):
    """Dependency factory — enforce a minimum subscription tier."""
    tier_order = {
        SubscriptionTier.EXPLORER: 0,
        SubscriptionTier.STRATEGIST: 1,
        SubscriptionTier.QUANT: 2,
    }

    async def _check(user: User = Depends(get_current_user)) -> User:
        if tier_order[user.tier] < tier_order[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum.value} tier or above",
            )
        if not user.is_subscription_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription expired",
            )
        return user

    return _check


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency — allow only wallets in the admin allowlist."""
    admin_wallets = [w.lower() for w in _settings.admin_wallets]
    if user.wallet_address.lower() not in admin_wallets:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
