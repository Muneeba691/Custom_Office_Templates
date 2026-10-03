import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.modules.tasks.schemas import TaskCreate, TaskOut, TaskStatusChange, TaskUpdate
from app.modules.tasks.service import (
    InvalidTransitionError,
    TaskNotFoundError,
    UserNotInTenantError,
    WorkerNotInTenantError,
    change_task_status,
    create_task,
    get_task,
    list_tasks,
    soft_delete_task,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

WRITE_ROLES = ("OWNER", "ADMIN", "HR", "LEGAL", "COMPLIANCE", "MANAGER")
READ_ROLES = ("OWNER", "ADMIN", "HR", "LEGAL", "COMPLIANCE", "MANAGER", "AUDITOR", "EXECUTIVE")


def _map_ref_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkerNotInTenantError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_WORKER", "message": str(exc)}},
        )
    if isinstance(exc, UserNotInTenantError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_USER", "message": str(exc)}},
        )
    raise exc


@router.post(
    "",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_task_endpoint(
    payload: TaskCreate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_task(
            db,
            tenant_id=ctx.tenant_id,
            title=payload.title,
            assigned_to_user_id=payload.assigned_to_user_id,
            due_date=payload.due_date,
            worker_id=payload.worker_id,
        )
    except (WorkerNotInTenantError, UserNotInTenantError) as exc:
        raise _map_ref_error(exc)


@router.get(
    "",
    response_model=list[TaskOut],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_tasks_endpoint(
    worker_id: uuid.UUID | None = Query(default=None),
    assigned_to_user_id: uuid.UUID | None = Query(default=None),
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_tasks(
        db,
        ctx.tenant_id,
        worker_id=worker_id,
        assigned_to_user_id=assigned_to_user_id,
    )


@router.get(
    "/{task_id}",
    response_model=TaskOut,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_task_endpoint(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task(db, ctx.tenant_id, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}},
        )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_task_endpoint(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await update_task(
            db,
            ctx.tenant_id,
            task_id,
            **payload.model_dump(exclude_unset=True),
        )
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}},
        )
    except (WorkerNotInTenantError, UserNotInTenantError) as exc:
        raise _map_ref_error(exc)


@router.patch(
    "/{task_id}/status",
    response_model=TaskOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def change_task_status_endpoint(
    task_id: uuid.UUID,
    payload: TaskStatusChange,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await change_task_status(
            db,
            ctx.tenant_id,
            task_id,
            new_status=payload.new_status,
        )
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}},
        )
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(exc)}},
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def delete_task_endpoint(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        await soft_delete_task(db, ctx.tenant_id, task_id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}},
        )
