import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkerType(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    CONTRACTOR = "CONTRACTOR"


class WorkerStatus(str, Enum):
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    OFFBOARDING = "OFFBOARDING"
    TERMINATED = "TERMINATED"


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    work_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    worker_type: Mapped[WorkerType] = mapped_column(
        SAEnum(WorkerType, name="worker_type"),
        nullable=False,
    )

    status: Mapped[WorkerStatus] = mapped_column(
        SAEnum(WorkerStatus, name="worker_status"),
        nullable=False,
        default=WorkerStatus.ONBOARDING,
    )

    role_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wrorkers.id"),
        nullable=True,
        index=True,
    )

    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Worker id={self.id} "
            f"full_name={self.full_name} "
            f"worker_type={self.worker_type} "
            f"status={self.status}>"
        )
