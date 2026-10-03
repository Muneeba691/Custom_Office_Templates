import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.compensation.models import CompensationFrequency, CompensationType


class CompensationCreate(BaseModel):
    worker_id: uuid.UUID
    compensation_type: CompensationType
    amount: Decimal
    currency: str
    frequency: CompensationFrequency
    effective_date: date
    end_date: date | None = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-letter ISO 4217 code, e.g. 'USD', 'PKR'")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be greater than zero")
        return v


class CompensationUpdate(BaseModel):
    amount: Decimal | None = None
    end_date: date | None = None


class CompensationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    worker_id: uuid.UUID
    compensation_type: CompensationType
    amount: Decimal
    currency: str
    frequency: CompensationFrequency
    effective_date: date
    end_date: date | None
    created_at: datetime
    updated_at: datetime
