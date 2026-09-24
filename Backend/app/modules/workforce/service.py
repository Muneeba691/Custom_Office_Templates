import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workforce.models import Worker, WorkerStatus


class WorkerNotFoundError(Exception):
    pass


async def get_worker(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> Worker | None:
    result = await db.execute(
        select(Worker).where(
            Worker.id == worker_id,
            Worker.tenant_id == tenant_id,
            Worker.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_workers(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[Worker]:
    result = await db.execute(
        select(Worker)
        .where(
            Worker.tenant_id == tenant_id,
            Worker.is_deleted == False,
        )
        .order_by(Worker.created_at.desc())
    )
    return list(result.scalars().all())


async def create_worker(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    full_name: str,
    email: str,
    country: str,
    worker_type,
    role_title: str | None = None,
    manager_id: uuid.UUID | None = None,
) -> Worker:
    worker = Worker(
        tenant_id=tenant_id,
        full_name=full_name,
        email=email,
        country=country,
        worker_type=worker_type,
        role_title=role_title,
        manager_id=manager_id,
        status=WorkerStatus.ONBOARDING,
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return worker


async def update_worker(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    worker_id: uuid.UUID,
    **fields,
) -> Worker:
    worker = await get_worker(db, tenant_id, worker_id)
    if worker is None:
        raise WorkerNotFoundError(f"Worker {worker_id} not found")

    for key, value in fields.items():
        setattr(worker, key, value)

    await db.commit()
    await db.refresh(worker)
    return worker


async def update_worker_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    worker_id: uuid.UUID,
    new_status: WorkerStatus,
) -> Worker:
    worker = await get_worker(db, tenant_id, worker_id)
    if worker is None:
        raise WorkerNotFoundError(f"Worker {worker_id} not found")

    worker.status = new_status
    await db.commit()
    await db.refresh(worker)
    return worker


async def soft_delete_worker(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    worker_id: uuid.UUID,
) -> None:
    worker = await get_worker(db, tenant_id, worker_id)
    if worker is None:
        raise WorkerNotFoundError(f"Worker {worker_id} not found")

    worker.is_deleted = True
    await db.commit()
