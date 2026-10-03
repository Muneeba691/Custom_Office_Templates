import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.modules.alerts.schemas import AlertCreate, AlertOut, AlertUpdate
from app.modules.alerts.service import (
    AlertNotFoundError,
    create_alert,
    get_alert,
    list_alerts,
    mark_alert_read,
    soft_delete_alert,
    update_alert,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])

WRITE_ROLES = ("OWNER", "ADMIN", "HR", "LEGAL", "COMPLIANCE", "MANAGER")
READ_ROLES = ("OWNER", "ADMIN", "HR", "LEGAL", "COMPLIANCE", "MANAGER", "AUDITOR", "EXECUTIVE")


@router.post(
    "",
    response_model=AlertOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_alert_endpoint(
    payload: AlertCreate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await create_alert(
        db,
        tenant_id=ctx.tenant_id,
        alert_type=payload.alert_type,
        severity=payload.severity,
        message=payload.message,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
    )


@router.get(
    "",
    response_model=list[AlertOut],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_alerts_endpoint(
    is_read: bool | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_alerts(
        db,
        ctx.tenant_id,
        is_read=is_read,
        alert_type=alert_type,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertOut,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_alert_endpoint(
    alert_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    alert = await get_alert(db, ctx.tenant_id, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ALERT_NOT_FOUND", "message": "Alert not found"}},
        )
    return alert


@router.patch(
    "/{alert_id}",
    response_model=AlertOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_alert_endpoint(
    alert_id: uuid.UUID,
    payload: AlertUpdate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await update_alert(
            db,
            ctx.tenant_id,
            alert_id,
            **payload.model_dump(exclude_unset=True),
        )
    except AlertNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ALERT_NOT_FOUND", "message": "Alert not found"}},
        )


@router.post(
    "/{alert_id}/read",
    response_model=AlertOut,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def mark_alert_read_endpoint(
    alert_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await mark_alert_read(db, ctx.tenant_id, alert_id)
    except AlertNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ALERT_NOT_FOUND", "message": "Alert not found"}},
        )


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def delete_alert_endpoint(
    alert_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        await soft_delete_alert(db, ctx.tenant_id, alert_id)
    except AlertNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ALERT_NOT_FOUND", "message": "Alert not found"}},
        )
