from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.tenant.schemas import TenantCreate, TenantOut
from app.modules.tenant.service import SlugAlreadyExistsError, create_tenant

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant_endpoint(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        tenant = await create_tenant(db, payload)
    except SlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "SLUG_TAKEN", "message": str(exc)}},
        )
    return tenant
