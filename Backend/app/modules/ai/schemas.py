import uuid
from typing import Any

from pydantic import BaseModel, Field


class DocumentVerificationAssistRequest(BaseModel):
    document_id: uuid.UUID


class Citation(BaseModel):
    resource_type: str
    resource_id: uuid.UUID
    summary: str


class AIAssistResponse(BaseModel):
    feature: str
    ai_configured: bool
    confidence: str
    content: str
    citations: list[Citation]
    suggestions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComplianceSuggestionRequest(BaseModel):
    worker_id: uuid.UUID
    rule_key: str | None = None


class NaturalLanguageQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
