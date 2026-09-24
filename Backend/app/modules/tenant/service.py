from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenant.models import Tenant
from app.modules.tenant.schemas import TenantCreate


class SlugAlreadyExistsError(Exception):
    pass


async def create_tenant(db: AsyncSession, payload: TenantCreate) -> Tenant:
    existing = await db.execute(select(Tenant).where(Tenant.slug == payload.slug))
    if existing.scalar_one_or_none() is not None:
        raise SlugAlreadyExistsError(f"Tenant slug '{payload.slug}' already exists")

    tenant = Tenant(name=payload.name, slug=payload.slug)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def get_tenant_by_id(db: AsyncSession, tenant_id) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False)
    )
    return result.scalar_one_or_none()
