import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tasks.models import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    assigned_to_user_id: uuid.UUID | None = None
    due_date: date | None = None
    worker_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    assigned_to_user_id: uuid.UUID | None = None
    due_date: date | None = None
    worker_id: uuid.UUID | None = None


class TaskStatusChange(BaseModel):
    new_status: TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    worker_id: uuid.UUID | None
    assigned_to_user_id: uuid.UUID | None
    title: str
    due_date: date | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
