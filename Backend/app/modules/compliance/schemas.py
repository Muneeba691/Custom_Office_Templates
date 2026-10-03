import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.compliance.models import CaseStatus, EvaluationStatus


class ComplianceRuleCreate(BaseModel):
    country: str
    rule_key: str
    rule_value: dict[str, Any]
    is_active: bool = True

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError(
                "country must be a 2-letter ISO 3166-1 alpha-2 code, e.g. 'PK', 'US'"
            )
        return v

    @field_validator("rule_key")
    @classmethod
    def validate_rule_key(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("rule_key must not be empty")
        return v


class ComplianceRuleUpdate(BaseModel):
    rule_value: dict[str, Any] | None = None
    is_active: bool | None = None


class ComplianceRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    country: str
    rule_key: str
    rule_value: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ComplianceEvaluateRequest(BaseModel):
    worker_id: uuid.UUID
    rule_key: str

    @field_validator("rule_key")
    @classmethod
    def validate_rule_key(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("rule_key must not be empty")
        return v


class ComplianceCaseStatusChange(BaseModel):
    new_status: CaseStatus
    notes: str | None = None


class ComplianceCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    worker_id: uuid.UUID
    rule_id: uuid.UUID | None
    rule_key: str
    evaluation_status: EvaluationStatus
    status: CaseStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
