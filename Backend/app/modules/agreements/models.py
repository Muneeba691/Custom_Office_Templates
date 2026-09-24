import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgreementStatus(str, Enum):
    DRAFT = "DRAFT"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    APPROVED = "APPROVED"
    SENT = "SENT"
    SIGNED = "SIGNED"
    ACTIVE = "ACTIVE"
    EXPIRING = "EXPIRING"
    RENEWED = "RENEWED"
    TERMINATED = "TERMINATED"


ALLOWED_TRANSITIONS: dict[AgreementStatus, set[AgreementStatus]] = {
    AgreementStatus.DRAFT: {AgreementStatus.INTERNAL_REVIEW, AgreementStatus.TERMINATED},
    AgreementStatus.INTERNAL_REVIEW: {AgreementStatus.APPROVED, AgreementStatus.DRAFT, AgreementStatus.TERMINATED},
    AgreementStatus.APPROVED: {AgreementStatus.SENT, AgreementStatus.TERMINATED},
    AgreementStatus.SENT: {AgreementStatus.SIGNED, AgreementStatus.DRAFT, AgreementStatus.TERMINATED},
    AgreementStatus.SIGNED: {AgreementStatus.ACTIVE, AgreementStatus.TERMINATED},
    AgreementStatus.ACTIVE: {AgreementStatus.EXPIRING, AgreementStatus.TERMINATED},
    AgreementStatus.EXPIRING: {AgreementStatus.RENEWED, AgreementStatus.TERMINATED},
    AgreementStatus.RENEWED: {AgreementStatus.ACTIVE, AgreementStatus.EXPIRING, AgreementStatus.TERMINATED},
    AgreementStatus.TERMINATED: set(),
}


class AgreementType(str, Enum):
    EMPLOYMENT_CONTRACT = "EMPLOYMENT_CONTRACT"
    CONTRACTOR_AGREEMENT = "CONTRACTOR_AGREEMENT"
    NDA = "NDA"
    AMENDMENT = "AMENDMENT"
    OTHER = "OTHER"


class Agreement(Base):
    __tablename__ = "agreements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    agreement_type: Mapped[AgreementType] = mapped_column(
        SAEnum(AgreementType, name="agreement_type"),
        nullable=False,
    )

    status: Mapped[AgreementStatus] = mapped_column(
        SAEnum(AgreementStatus, name="agreement_status"),
        nullable=False,
        default=AgreementStatus.DRAFT,
    )

    effective_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    expiry_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    terminated_reason: Mapped[str | None] = mapped_column(
        String(1000),
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
            f"<Agreement id={self.id} "
            f"title={self.title} "
            f"status={self.status}>"
        )
