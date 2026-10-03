import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvaluationStatus(str, Enum):
    KNOWN = "KNOWN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"


ALLOWED_CASE_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.OPEN: {CaseStatus.UNDER_REVIEW, CaseStatus.RESOLVED},
    CaseStatus.UNDER_REVIEW: {CaseStatus.OPEN, CaseStatus.RESOLVED},
    CaseStatus.RESOLVED: set(),
}


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "country",
            "rule_key",
            name="uq_compliance_rules_tenant_country_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
    )

    rule_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    rule_value: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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
            f"<ComplianceRule id={self.id} "
            f"country={self.country} "
            f"rule_key={self.rule_key}>"
        )


class ComplianceCase(Base):
    __tablename__ = "compliance_cases"

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

    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    rule_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    evaluation_status: Mapped[EvaluationStatus] = mapped_column(
        SAEnum(EvaluationStatus, name="compliance_evaluation_status"),
        nullable=False,
    )

    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, name="compliance_case_status"),
        nullable=False,
        default=CaseStatus.OPEN,
    )

    notes: Mapped[str | None] = mapped_column(
        String(2000),
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
            f"<ComplianceCase id={self.id} "
            f"rule_key={self.rule_key} "
            f"evaluation={self.evaluation_status} "
            f"status={self.status}>"
        )
