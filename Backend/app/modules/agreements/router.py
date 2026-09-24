import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.core.esignature import ESignatureNotConfiguredError, get_esignature_provider
from app.modules.agreements.schemas import (
    AgreementCreate,
    AgreementOut,
    AgreementStatusChange,
    AgreementUpdate,
)
from app.modules.agreements.service import (
    AgreementNotFoundError,
    InvalidTransitionError,
    TerminationReasonRequiredError,
    WorkerNotInTenantError,
    change_status,
    create_agreement,
    get_agreement,
    list_agreements_for_worker,
    send_for_signature,
    soft_delete_agreement,
    update_agreement,
)

router = APIRouter(prefix="/agreements", tags=["agreements"])

WRITE_ROLES = ("OWNER", "ADMIN", "HR", "LEGAL")
STATUS_ROLES = ("OWNER", "ADMIN", "HR", "LEGAL")


@router.post(
    "",
    response_model=AgreementOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_agreement_endpoint(
    payload: AgreementCreate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        agreement = await create_agreement(
            db,
            tenant_id=ctx.tenant_id,
            worker_id=payload.worker_id,
            title=payload.title,
            agreement_type=payload.agreement_type,
            effective_date=payload.effective_date,
            expiry_date=payload.expiry_date,
        )
    except WorkerNotInTenantError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_WORKER", "message": str(exc)}},
        )
    return agreement


@router.get("/worker/{worker_id}", response_model=list[AgreementOut])
async def list_worker_agreements_endpoint(
    worker_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_agreements_for_worker(db, ctx.tenant_id, worker_id)


@router.get("/{agreement_id}", response_model=AgreementOut)
async def get_agreement_endpoint(
    agreement_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    agreement = await get_agreement(db, ctx.tenant_id, agreement_id)
    if agreement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "AGREEMENT_NOT_FOUND", "message": "Agreement not found"}},
        )
    return agreement


@router.patch(
    "/{agreement_id}",
    response_model=AgreementOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_agreement_endpoint(
    agreement_id: uuid.UUID,
    payload: AgreementUpdate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        agreement = await update_agreement(
            db,
            ctx.tenant_id,
            agreement_id,
            **payload.model_dump(exclude_unset=True),
        )
    except AgreementNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "AGREEMENT_NOT_FOUND", "message": "Agreement not found"}},
        )
    return agreement


@router.patch(
    "/{agreement_id}/status",
    response_model=AgreementOut,
    dependencies=[Depends(require_roles(*STATUS_ROLES))],
)
async def change_status_endpoint(
    agreement_id: uuid.UUID,
    payload: AgreementStatusChange,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        agreement = await change_status(
            db,
            ctx.tenant_id,
            agreement_id,
            new_status=payload.new_status,
            reason=payload.reason,
        )
    except AgreementNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "AGREEMENT_NOT_FOUND", "message": "Agreement not found"}},
        )
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(exc)}},
        )
    except TerminationReasonRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "REASON_REQUIRED", "message": str(exc)}},
        )
    return agreement


@router.delete(
    "/{agreement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def delete_agreement_endpoint(
    agreement_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        await soft_delete_agreement(db, ctx.tenant_id, agreement_id)
    except AgreementNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "AGREEMENT_NOT_FOUND", "message": "Agreement not found"}},
        )


class SendForSignaturePayload(BaseModel):
    signer_email: str
    signer_name: str


@router.post(
    "/{agreement_id}/send-for-signature",
    response_model=AgreementOut,
    dependencies=[Depends(require_roles(*STATUS_ROLES))],
)
async def send_for_signature_endpoint(
    agreement_id: uuid.UUID,
    payload: SendForSignaturePayload,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    provider = get_esignature_provider()
    try:
        agreement = await send_for_signature(
            db,
            ctx.tenant_id,
            agreement_id,
            esignature_provider=provider,
            signer_email=payload.signer_email,
            signer_name=payload.signer_name,
        )
    except AgreementNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "AGREEMENT_NOT_FOUND", "message": "Agreement not found"}},
        )
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(exc)}},
        )
    except ESignatureNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"error": {"code": "ESIGNATURE_NOT_CONFIGURED", "message": str(exc)}},
        )
    return agreement
