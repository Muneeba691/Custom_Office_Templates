import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agreements.models import (
    ALLOWED_TRANSITIONS,
    Agreement,
    AgreementStatus,
)
from app.modules.workforce.models import Worker


class AgreementNotFoundError(Exception):
    pass


class WorkerNotInTenantError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


class TerminationReasonRequiredError(Exception):
    pass


async def _validate_worker_in_tenant(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Worker.id).where(
            Worker.id == worker_id,
            Worker.tenant_id == tenant_id,
            Worker.is_deleted == False,
        )
    )
    if result.scalar_one_or_none() is None:
        raise WorkerNotInTenantError(
            f"Worker {worker_id} does not belong to this tenant"
        )


async def get_agreement(
    db: AsyncSession, tenant_id: uuid.UUID, agreement_id: uuid.UUID
) -> Agreement | None:
    result = await db.execute(
        select(Agreement).where(
            Agreement.id == agreement_id,
            Agreement.tenant_id == tenant_id,
            Agreement.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_agreements_for_worker(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> list[Agreement]:
    result = await db.execute(
        select(Agreement)
        .where(
            Agreement.tenant_id == tenant_id,
            Agreement.worker_id == worker_id,
            Agreement.is_deleted == False,
        )
        .order_by(Agreement.created_at.desc())
    )
    return list(result.scalars().all())


async def create_agreement(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    worker_id: uuid.UUID,
    title: str,
    agreement_type,
    effective_date=None,
    expiry_date=None,
) -> Agreement:
    await _validate_worker_in_tenant(db, tenant_id, worker_id)

    agreement = Agreement(
        tenant_id=tenant_id,
        worker_id=worker_id,
        title=title,
        agreement_type=agreement_type,
        status=AgreementStatus.DRAFT,
        effective_date=effective_date,
        expiry_date=expiry_date,
    )
    db.add(agreement)
    await db.commit()
    await db.refresh(agreement)
    return agreement


async def update_agreement(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agreement_id: uuid.UUID,
    **fields,
) -> Agreement:
    agreement = await get_agreement(db, tenant_id, agreement_id)
    if agreement is None:
        raise AgreementNotFoundError(f"Agreement {agreement_id} not found")

    for key, value in fields.items():
        setattr(agreement, key, value)

    await db.commit()
    await db.refresh(agreement)
    return agreement


async def change_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agreement_id: uuid.UUID,
    new_status: AgreementStatus,
    reason: str | None = None,
) -> Agreement:
    agreement = await get_agreement(db, tenant_id, agreement_id)
    if agreement is None:
        raise AgreementNotFoundError(f"Agreement {agreement_id} not found")

    current_status = agreement.status
    allowed_next = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed_next:
        raise InvalidTransitionError(
            f"Cannot transition from {current_status.value} to {new_status.value}"
        )

    if new_status == AgreementStatus.TERMINATED and not reason:
        raise TerminationReasonRequiredError(
            "A reason is required when terminating an agreement"
        )

    agreement.status = new_status
    if new_status == AgreementStatus.TERMINATED:
        agreement.terminated_reason = reason

    await db.commit()
    await db.refresh(agreement)
    return agreement


async def soft_delete_agreement(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agreement_id: uuid.UUID,
) -> None:
    agreement = await get_agreement(db, tenant_id, agreement_id)
    if agreement is None:
        raise AgreementNotFoundError(f"Agreement {agreement_id} not found")

    agreement.is_deleted = True
    await db.commit()


async def send_for_signature(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agreement_id: uuid.UUID,
    esignature_provider,
    signer_email: str,
    signer_name: str,
) -> Agreement:
    agreement = await get_agreement(db, tenant_id, agreement_id)
    if agreement is None:
        raise AgreementNotFoundError(f"Agreement {agreement_id} not found")

    current_status = agreement.status
    if AgreementStatus.SENT not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise InvalidTransitionError(
            f"Cannot send for signature from status {current_status.value}"
        )

    esignature_provider.send_for_signature(
        document_key=str(agreement.id),
        signer_email=signer_email,
        signer_name=signer_name,
    )

    agreement.status = AgreementStatus.SENT
    await db.commit()
    await db.refresh(agreement)
    return agreement
