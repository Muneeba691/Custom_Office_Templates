from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.modules.identity.models import User, UserRole
from app.modules.identity.schemas import RegisterRequest
from app.modules.tenant.models import Tenant


class TenantNotFoundError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AccountInactiveError(Exception):
    pass


async def _get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.is_deleted == False)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    tenant = await _get_tenant_by_slug(db, payload.tenant_slug)
    if tenant is None:
        raise TenantNotFoundError(f"No tenant with slug '{payload.tenant_slug}'")

    existing = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == payload.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise EmailAlreadyRegisteredError("Email already registered for this tenant")

    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.tenant_id == tenant.id)
    )
    is_first_user = (count_result.scalar_one() or 0) == 0

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER if is_first_user else UserRole.WORKER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, tenant_slug: str, email: str, password: str
) -> tuple[str, str]:
    tenant = await _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise InvalidCredentialsError("Invalid credentials")

    result = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == email)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Invalid credentials")

    if not user.is_active:
        raise AccountInactiveError("Account is deactivated")

    access_token = create_access_token(
        user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role.value
    )
    refresh_token = create_refresh_token(user_id=str(user.id))
    return access_token, refresh_token


async def get_user_by_id(db: AsyncSession, user_id) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)  # noqa: E712
    )
    return result.scalar_one_or_none()
