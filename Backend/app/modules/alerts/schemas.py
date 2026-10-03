import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.alerts.models import AlertSeverity


class AlertCreate(BaseModel):
    alert_type: str = Field(..., min_length=1, max_length=100)
    severity: AlertSeverity
    message: str = Field(..., min_length=1, max_length=2000)
    related_entity_type: str | None = Field(default=None, max_length=100)
    related_entity_id: uuid.UUID | None = None


class AlertUpdate(BaseModel):
    is_read: bool | None = None
    message: str | None = Field(default=None, min_length=1, max_length=2000)


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    alert_type: str
    severity: AlertSeverity
    message: str
    is_read: bool
    related_entity_type: str | None
    related_entity_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
