import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.alerts.models import Alert, AlertSeverity


class AlertNotFoundError(Exception):
    pass


async def get_alert(
    db: AsyncSession, tenant_id: uuid.UUID, alert_id: uuid.UUID
) -> Alert | None:
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id,
            Alert.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_alerts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    is_read: bool | None = None,
    alert_type: str | None = None,
) -> list[Alert]:
    stmt = select(Alert).where(
        Alert.tenant_id == tenant_id,
        Alert.is_deleted == False,  # noqa: E712
    )
    if is_read is not None:
        stmt = stmt.where(Alert.is_read == is_read)
    if alert_type is not None:
        stmt = stmt.where(Alert.alert_type == alert_type)
    result = await db.execute(stmt.order_by(Alert.created_at.desc()))
    return list(result.scalars().all())


async def create_alert(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    alert_type: str,
    severity: AlertSeverity,
    message: str,
    related_entity_type: str | None = None,
    related_entity_id: uuid.UUID | None = None,
) -> Alert:
    alert = Alert(
        tenant_id=tenant_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        is_read=False,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def update_alert(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    **fields,
) -> Alert:
    alert = await get_alert(db, tenant_id, alert_id)
    if alert is None:
        raise AlertNotFoundError(f"Alert {alert_id} not found")

    for key, value in fields.items():
        setattr(alert, key, value)

    await db.commit()
    await db.refresh(alert)
    return alert


async def mark_alert_read(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
) -> Alert:
    return await update_alert(db, tenant_id, alert_id, is_read=True)


async def soft_delete_alert(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
) -> None:
    alert = await get_alert(db, tenant_id, alert_id)
    if alert is None:
        raise AlertNotFoundError(f"Alert {alert_id} not found")

    alert.is_deleted = True
    await db.commit()
