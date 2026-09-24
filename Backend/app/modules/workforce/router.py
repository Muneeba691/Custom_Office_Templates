import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.modules.workforce.schemas import (
    WorkerCreate,
    WorkerOut,
    WorkerStatusUpdate,
    WorkerUpdate,
)
from app.modules.workforce.service import (
    WorkerNotFoundError,
    create_worker,
    get_worker,
    list_workers,
    soft_delete_worker,
    update_worker,
    update_worker_status,
)

router = APIRouter(prefix="/workforce", tags=["workforce"])

# Write operations (create/update/delete) sirf ye roles kar sakte hain.
# Documents module ke WRITE_ROLES se match karta hai — HR aur Admin
# workforce data manage karte hain, Worker khud apna record nahi badal sakta.
WRITE_ROLES = ("OWNER", "ADMIN", "HR")


@router.post(
    "",
    response_model=WorkerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_worker_endpoint(
    payload: WorkerCreate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    worker = await create_worker(
        db,
        tenant_id=ctx.tenant_id,
        full_name=payload.full_name,
        email=payload.email,
        country=payload.country,
        worker_type=payload.worker_type,
        role_title=payload.role_title,
        manager_id=payload.manager_id,
    )
    return worker


@router.get("", response_model=list[WorkerOut])
async def list_workers_endpoint(
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_workers(db, ctx.tenant_id)


@router.get("/{worker_id}", response_model=WorkerOut)
async def get_worker_endpoint(
    worker_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    worker = await get_worker(db, ctx.tenant_id, worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "WORKER_NOT_FOUND", "message": "Worker not found"}},
        )
    return worker


@router.patch(
    "/{worker_id}",
    response_model=WorkerOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_worker_endpoint(
    worker_id: uuid.UUID,
    payload: WorkerUpdate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        worker = await update_worker(
            db,
            ctx.tenant_id,
            worker_id,
            **payload.model_dump(exclude_unset=True),
        )
    except WorkerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "WORKER_NOT_FOUND", "message": "Worker not found"}},
        )
    return worker


@router.patch(
    "/{worker_id}/status",
    response_model=WorkerOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_worker_status_endpoint(
    worker_id: uuid.UUID,
    payload: WorkerStatusUpdate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        worker = await update_worker_status(
            db, ctx.tenant_id, worker_id, payload.status
        )
    except WorkerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "WORKER_NOT_FOUND", "message": "Worker not found"}},
        )
    return worker


@router.delete(
    "/{worker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def delete_worker_endpoint(
    worker_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        await soft_delete_worker(db, ctx.tenant_id, worker_id)
    except WorkerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "WORKER_NOT_FOUND", "message": "Worker not found"}},
        )
