import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.agreements.models import AgreementStatus, AgreementType


class AgreementCreate(BaseModel):
    worker_id: uuid.UUID
    title: str
    agreement_type: AgreementType
    effective_date: date | None = None
    expiry_date: date | None = None


class AgreementUpdate(BaseModel):
    title: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None


class AgreementStatusChange(BaseModel):
    new_status: AgreementStatus
    reason: str | None = None


class AgreementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    worker_id: uuid.UUID
    document_id: uuid.UUID | None
    title: str
    agreement_type: AgreementType
    status: AgreementStatus
    effective_date: date | None
    expiry_date: date | None
    signed_at: datetime | None
    terminated_reason: str | None
    created_at: datetime
    updated_at: datetime
