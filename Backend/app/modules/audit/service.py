import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent


class AuditEventNotFoundError(Exception):
    pass


class AuditMutationRejectedError(Exception):
    """Audit events are insert-only. Updates and deletes are forbidden."""


async def record_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    performed_by_user_id: uuid.UUID | None = None,
    changes: dict[str, Any] | None = None,
    *,
    commit: bool = True,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=tenant_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by_user_id=performed_by_user_id,
        changes=changes,
    )
    db.add(event)
    if commit:
        await db.commit()
        await db.refresh(event)
    else:
        await db.flush()
    return event


async def get_event(
    db: AsyncSession, tenant_id: uuid.UUID, event_id: uuid.UUID
) -> AuditEvent | None:
    result = await db.execute(
        select(AuditEvent).where(
            AuditEvent.id == event_id,
            AuditEvent.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def list_events(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: str | None = None,
) -> list[AuditEvent]:
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if entity_type is not None:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if action is not None:
        stmt = stmt.where(AuditEvent.action == action)
    result = await db.execute(stmt.order_by(AuditEvent.occurred_at.desc()))
    return list(result.scalars().all())


def reject_mutation() -> None:
    raise AuditMutationRejectedError("Audit events are immutable and cannot be changed")
