import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tenant.models import TenantStatus


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
