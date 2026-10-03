import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.compensation.models import CompensationRecord
from app.modules.workforce.models import Worker


class CompensationNotFoundError(Exception):
    pass


class WorkerNotInTenantError(Exception):
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


async def get_compensation(
    db: AsyncSession, tenant_id: uuid.UUID, record_id: uuid.UUID
) -> CompensationRecord | None:
    result = await db.execute(
        select(CompensationRecord).where(
            CompensationRecord.id == record_id,
            CompensationRecord.tenant_id == tenant_id,
            CompensationRecord.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_compensation_for_worker(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> list[CompensationRecord]:
    result = await db.execute(
        select(CompensationRecord)
        .where(
            CompensationRecord.tenant_id == tenant_id,
            CompensationRecord.worker_id == worker_id,
            CompensationRecord.is_deleted == False,
        )
        .order_by(CompensationRecord.effective_date.desc())
    )
    return list(result.scalars().all())


async def create_compensation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    worker_id: uuid.UUID,
    compensation_type,
    amount,
    currency: str,
    frequency,
    effective_date,
    end_date=None,
) -> CompensationRecord:
    await _validate_worker_in_tenant(db, tenant_id, worker_id)

    record = CompensationRecord(
        tenant_id=tenant_id,
        worker_id=worker_id,
        compensation_type=compensation_type,
        amount=amount,
        currency=currency,
        frequency=frequency,
        effective_date=effective_date,
        end_date=end_date,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_compensation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    record_id: uuid.UUID,
    **fields,
) -> CompensationRecord:
    record = await get_compensation(db, tenant_id, record_id)
    if record is None:
        raise CompensationNotFoundError(f"Compensation record {record_id} not found")

    for key, value in fields.items():
        setattr(record, key, value)

    await db.commit()
    await db.refresh(record)
    return record


async def soft_delete_compensation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    record_id: uuid.UUID,
) -> None:
    record = await get_compensation(db, tenant_id, record_id)
    if record is None:
        raise CompensationNotFoundError(f"Compensation record {record_id} not found")

    record.is_deleted = True
    await db.commit()
