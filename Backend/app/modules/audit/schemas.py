import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    performed_by_user_id: uuid.UUID | None
    changes: dict[str, Any] | None
    occurred_at: datetime
