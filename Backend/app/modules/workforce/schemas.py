import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.modules.workforce.models import WorkerStatus, WorkerType


class WorkerCreate(BaseModel):
    """
    Client jo bhejta hai jab naya worker banate hain.
    NOTE: tenant_id yahan jaan-boojh kar NAHI hai.
    tenant_id sirf JWT (TenantContext) se aayega, router mein — kabhi bhi
    client-supplied body se nahi. Agar hum ye field yahan add kar dein,
    to koi malicious client apna tenant_id ke jagah kisi aur tenant ka
    UUID bhej kar cross-tenant data create kar sakta hai.
    """

    full_name: str
    email: EmailStr
    country: str
    work_location: str | None = None
    worker_type: WorkerType
    role_title: str | None = None
    manager_id: uuid.UUID | None = None
    start_date: date | None = None

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """
        Country ko hum ISO 3166-1 alpha-2 format mein rakhte hain (jaise 'PK', 'US').
        Model mein String(2) hai — agar client 'Pakistan' ya 'pk' bhej de,
        database constraint fail hoga ya galat data store hoga.
        Yahan hi normalize aur validate kar dena behtar hai — error clear
        aur turant milta hai, database tak jaane se pehle.
        """
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError(
                "country must be a 2-letter ISO 3166-1 alpha-2 code, e.g. 'PK', 'US'"
            )
        return v


class WorkerUpdate(BaseModel):
    """
    Partial update schema — sab fields optional hain (PATCH semantics).
    Jo field client bhejta hi nahi (None reh jaye), wo service layer mein
    ignore hoga, overwrite nahi karega existing value ko.

    NOTE: 'status' yahan jaan-boojh kar shamil NAHI hai. Worker lifecycle
    ko hum dedicated status-change endpoint se control karenge (neeche
    WorkerStatusUpdate), taake future mein agar hum status transitions
    pe rules lagayein (jaise TERMINATED se wapas ACTIVE na ho sake), to
    wo enforcement ek hi jagah ho — general update endpoint se bypass
    na ho sake.
    """

    full_name: str | None = None
    email: EmailStr | None = None
    work_location: str | None = None
    role_title: str | None = None
    manager_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


class WorkerStatusUpdate(BaseModel):
    """
    Sirf status change karne ke liye alag schema — is se hum future mein
    transition rules (Agreement jaisi ALLOWED_TRANSITIONS dict) yahan
    laga sakte hain bina general update endpoint ko chhue.
    """

    status: WorkerStatus


class WorkerOut(BaseModel):
    """
    Response schema — client ko jo wapas jata hai.
    model_config se hum SQLAlchemy ORM object ko seedha isi schema mein
    convert kar sakte hain (from_attributes=True), bina manually dict
    banaye.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    full_name: str
    email: str
    country: str
    work_location: str | None
    worker_type: WorkerType
    status: WorkerStatus
    role_title: str | None
    manager_id: uuid.UUID | None
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime
