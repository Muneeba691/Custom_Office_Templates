import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.modules.audit.schemas import AuditEventOut
from app.modules.audit.service import get_event, list_events

router = APIRouter(prefix="/audit-events", tags=["audit"])

READ_ROLES = ("OWNER", "ADMIN", "AUDITOR", "COMPLIANCE", "LEGAL")


@router.get(
    "",
    response_model=list[AuditEventOut],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_audit_events_endpoint(
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_events(
        db,
        ctx.tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
    )


@router.get(
    "/{event_id}",
    response_model=AuditEventOut,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_audit_event_endpoint(
    event_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    event = await get_event(db, ctx.tenant_id, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "AUDIT_EVENT_NOT_FOUND", "message": "Audit event not found"}},
        )
    return event


@router.patch("/{event_id}", include_in_schema=False)
async def reject_audit_update():
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail={
            "error": {
                "code": "AUDIT_IMMUTABLE",
                "message": "Audit events cannot be updated",
            }
        },
    )


@router.delete("/{event_id}", include_in_schema=False)
async def reject_audit_delete():
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail={
            "error": {
                "code": "AUDIT_IMMUTABLE",
                "message": "Audit events cannot be deleted",
            }
        },
    )
