import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.tasks.models import ALLOWED_TASK_TRANSITIONS, Task, TaskStatus
from app.modules.workforce.models import Worker


class TaskNotFoundError(Exception):
    pass


class WorkerNotInTenantError(Exception):
    pass


class UserNotInTenantError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


async def _validate_worker_in_tenant(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Worker.id).where(
            Worker.id == worker_id,
            Worker.tenant_id == tenant_id,
            Worker.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is None:
        raise WorkerNotInTenantError(
            f"Worker {worker_id} does not belong to this tenant"
        )


async def _validate_user_in_tenant(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(User.id).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is None:
        raise UserNotInTenantError(f"User {user_id} does not belong to this tenant")


async def get_task(db: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.tenant_id == tenant_id,
            Task.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    worker_id: uuid.UUID | None = None,
    assigned_to_user_id: uuid.UUID | None = None,
) -> list[Task]:
    stmt = select(Task).where(
        Task.tenant_id == tenant_id,
        Task.is_deleted == False,  # noqa: E712
    )
    if worker_id is not None:
        stmt = stmt.where(Task.worker_id == worker_id)
    if assigned_to_user_id is not None:
        stmt = stmt.where(Task.assigned_to_user_id == assigned_to_user_id)
    result = await db.execute(stmt.order_by(Task.created_at.desc()))
    return list(result.scalars().all())


async def create_task(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    title: str,
    assigned_to_user_id: uuid.UUID | None = None,
    due_date=None,
    worker_id: uuid.UUID | None = None,
) -> Task:
    if worker_id is not None:
        await _validate_worker_in_tenant(db, tenant_id, worker_id)
    if assigned_to_user_id is not None:
        await _validate_user_in_tenant(db, tenant_id, assigned_to_user_id)

    task = Task(
        tenant_id=tenant_id,
        title=title,
        assigned_to_user_id=assigned_to_user_id,
        due_date=due_date,
        worker_id=worker_id,
        status=TaskStatus.TODO,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID,
    **fields,
) -> Task:
    task = await get_task(db, tenant_id, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} not found")

    if "worker_id" in fields and fields["worker_id"] is not None:
        await _validate_worker_in_tenant(db, tenant_id, fields["worker_id"])
    if "assigned_to_user_id" in fields and fields["assigned_to_user_id"] is not None:
        await _validate_user_in_tenant(db, tenant_id, fields["assigned_to_user_id"])

    for key, value in fields.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return task


async def change_task_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID,
    new_status: TaskStatus,
) -> Task:
    task = await get_task(db, tenant_id, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} not found")

    allowed_next = ALLOWED_TASK_TRANSITIONS.get(task.status, set())
    if new_status not in allowed_next:
        raise InvalidTransitionError(
            f"Cannot transition from {task.status.value} to {new_status.value}"
        )

    task.status = new_status
    await db.commit()
    await db.refresh(task)
    return task


async def soft_delete_task(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID,
) -> None:
    task = await get_task(db, tenant_id, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} not found")

    task.is_deleted = True
    await db.commit()
