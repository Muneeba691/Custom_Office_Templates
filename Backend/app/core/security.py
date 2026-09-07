"""
Security primitives: password hashing and JWT handling.

This module is intentionally the ONLY place password hashing and
token encode/decode logic lives. Do not duplicate this logic elsewhere.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


class TokenPayloadError(Exception):
    """Raised when a token is invalid, expired, or malformed."""


def _create_token(
    subject: str,
    token_type: Literal["access", "refresh"],
    extra_claims: dict[str, Any] | None,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Access tokens carry tenant_id and role so authorization middleware
    can enforce tenant isolation and RBAC without an extra DB hit.
    NEVER trust a client-supplied tenant_id elsewhere in the app --
    this claim, once verified, is the only trusted source of tenant context.
    """
    claims = {"tenant_id": tenant_id, "role": role}
    if extra_claims:
        claims.update(extra_claims)
    return _create_token(
        subject=user_id,
        token_type="access",
        extra_claims=claims,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        token_type="refresh",
        extra_claims=None,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise TokenPayloadError(str(exc)) from exc
    return payload