import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.modules.compensation.schemas import (
    CompensationCreate,
    CompensationOut,
    CompensationUpdate,
)
from app.modules.compensation.service import (
    CompensationNotFoundError,
    WorkerNotInTenantError,
    create_compensation,
    get_compensation,
    list_compensation_for_worker,
    soft_delete_compensation,
    update_compensation,
)

router = APIRouter(prefix="/compensation", tags=["compensation"])

WRITE_ROLES = ("OWNER", "ADMIN", "FINANCE", "HR")
READ_ROLES = ("OWNER", "ADMIN", "FINANCE", "HR", "CFO", "AUDITOR")


@router.post(
    "",
    response_model=CompensationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_compensation_endpoint(
    payload: CompensationCreate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        record = await create_compensation(
            db,
            tenant_id=ctx.tenant_id,
            worker_id=payload.worker_id,
            compensation_type=payload.compensation_type,
            amount=payload.amount,
            currency=payload.currency,
            frequency=payload.frequency,
            effective_date=payload.effective_date,
            end_date=payload.end_date,
        )
    except WorkerNotInTenantError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_WORKER", "message": str(exc)}},
        )
    return record


@router.get(
    "/worker/{worker_id}",
    response_model=list[CompensationOut],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_worker_compensation_endpoint(
    worker_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_compensation_for_worker(db, ctx.tenant_id, worker_id)


@router.get(
    "/{record_id}",
    response_model=CompensationOut,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_compensation_endpoint(
    record_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    record = await get_compensation(db, ctx.tenant_id, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COMPENSATION_NOT_FOUND", "message": "Compensation record not found"}},
        )
    return record


@router.patch(
    "/{record_id}",
    response_model=CompensationOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_compensation_endpoint(
    record_id: uuid.UUID,
    payload: CompensationUpdate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        record = await update_compensation(
            db,
            ctx.tenant_id,
            record_id,
            **payload.model_dump(exclude_unset=True),
        )
    except CompensationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COMPENSATION_NOT_FOUND", "message": "Compensation record not found"}},
        )
    return record


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def delete_compensation_endpoint(
    record_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        await soft_delete_compensation(db, ctx.tenant_id, record_id)
    except CompensationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COMPENSATION_NOT_FOUND", "message": "Compensation record not found"}},
        )
