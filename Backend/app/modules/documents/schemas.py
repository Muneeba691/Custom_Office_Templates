import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.documents.models import DocumentStatus, DocumentType


class DocumentRequirementCreate(BaseModel):
    worker_id: uuid.UUID
    document_type: DocumentType
    expires_on: date | None = None


class DocumentUploadInit(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    file_size_bytes: int = Field(..., gt=0, le=25_000_000)


class DocumentUploadInitOut(BaseModel):
    upload_url: str
    storage_key: str
    expires_in_seconds: int


class DocumentReview(BaseModel):
    status: DocumentStatus = Field(..., description="Must be VERIFIED or REJECTED")


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    worker_id: uuid.UUID
    document_type: DocumentType
    status: DocumentStatus
    file_name: str | None
    content_type: str | None
    file_size_bytes: int | None
    version: int
    expires_on: date | None
    created_at: datetime
    updated_at: datetime
