from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context
from app.core.security import TokenPayloadError, create_access_token, decode_token
from app.modules.identity.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairOut,
    UserOut,
)
from app.modules.identity.service import (
    AccountInactiveError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    TenantNotFoundError,
    authenticate_user,
    get_user_by_id,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["identity"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_endpoint(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await register_user(db, payload)
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TENANT_NOT_FOUND", "message": str(exc)}},
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "EMAIL_TAKEN", "message": str(exc)}},
        )
    return user


@router.post("/login", response_model=TokenPairOut)
async def login_endpoint(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        access_token, refresh_token = await authenticate_user(
            db, payload.tenant_slug, payload.email, payload.password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": str(exc)}},
        )
    except AccountInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCOUNT_INACTIVE", "message": str(exc)}},
        )
    return TokenPairOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPairOut)
async def refresh_endpoint(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        token_payload = decode_token(payload.refresh_token)
    except TokenPayloadError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token is invalid or expired"}},
        )
    if token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN_TYPE", "message": "Refresh token required"}},
        )
    user = await get_user_by_id(db, UUID(token_payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token is invalid or expired"}},
        )
    access_token = create_access_token(
        user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role.value
    )
    return TokenPairOut(access_token=access_token, refresh_token=payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me_endpoint(
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, ctx.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "User no longer exists"}},
        )
    return user
