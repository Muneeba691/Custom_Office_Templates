import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.compliance.models import (
    ALLOWED_CASE_TRANSITIONS,
    CaseStatus,
    ComplianceCase,
    ComplianceRule,
    EvaluationStatus,
)
from app.modules.workforce.models import Worker


class RuleNotFoundError(Exception):
    pass


class RuleAlreadyExistsError(Exception):
    pass


class CaseNotFoundError(Exception):
    pass


class WorkerNotInTenantError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


def classify_rule_value(rule: ComplianceRule | None) -> EvaluationStatus:
    """Database-driven classification — no country-specific branches."""
    if rule is None:
        return EvaluationStatus.UNKNOWN

    value = rule.rule_value
    if not isinstance(value, dict) or not value:
        return EvaluationStatus.REVIEW_REQUIRED
    if value.get("ambiguous") is True or value.get("needs_review") is True:
        return EvaluationStatus.REVIEW_REQUIRED
    if "value" not in value:
        return EvaluationStatus.REVIEW_REQUIRED
    return EvaluationStatus.KNOWN


async def _validate_worker_in_tenant(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> Worker:
    result = await db.execute(
        select(Worker).where(
            Worker.id == worker_id,
            Worker.tenant_id == tenant_id,
            Worker.is_deleted == False,
        )
    )
    worker = result.scalar_one_or_none()
    if worker is None:
        raise WorkerNotInTenantError(
            f"Worker {worker_id} does not belong to this tenant"
        )
    return worker


async def get_rule(
    db: AsyncSession, tenant_id: uuid.UUID, rule_id: uuid.UUID
) -> ComplianceRule | None:
    result = await db.execute(
        select(ComplianceRule).where(
            ComplianceRule.id == rule_id,
            ComplianceRule.tenant_id == tenant_id,
            ComplianceRule.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def get_rule_by_country_and_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    country: str,
    rule_key: str,
) -> ComplianceRule | None:
    result = await db.execute(
        select(ComplianceRule).where(
            ComplianceRule.tenant_id == tenant_id,
            ComplianceRule.country == country,
            ComplianceRule.rule_key == rule_key,
            ComplianceRule.is_active == True,
            ComplianceRule.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_rules(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    country: str | None = None,
) -> list[ComplianceRule]:
    stmt = select(ComplianceRule).where(
        ComplianceRule.tenant_id == tenant_id,
        ComplianceRule.is_deleted == False,
    )
    if country is not None:
        stmt = stmt.where(ComplianceRule.country == country)
    result = await db.execute(stmt.order_by(ComplianceRule.created_at.desc()))
    return list(result.scalars().all())


async def create_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    country: str,
    rule_key: str,
    rule_value: dict[str, Any],
    is_active: bool = True,
) -> ComplianceRule:
    rule = ComplianceRule(
        tenant_id=tenant_id,
        country=country,
        rule_key=rule_key,
        rule_value=rule_value,
        is_active=is_active,
    )
    db.add(rule)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise RuleAlreadyExistsError(
            f"Rule {rule_key} already exists for country {country}"
        )
    await db.refresh(rule)
    return rule


async def update_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    **fields,
) -> ComplianceRule:
    rule = await get_rule(db, tenant_id, rule_id)
    if rule is None:
        raise RuleNotFoundError(f"Compliance rule {rule_id} not found")

    for key, value in fields.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return rule


async def soft_delete_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> None:
    rule = await get_rule(db, tenant_id, rule_id)
    if rule is None:
        raise RuleNotFoundError(f"Compliance rule {rule_id} not found")

    rule.is_deleted = True
    rule.is_active = False
    await db.commit()


async def get_case(
    db: AsyncSession, tenant_id: uuid.UUID, case_id: uuid.UUID
) -> ComplianceCase | None:
    result = await db.execute(
        select(ComplianceCase).where(
            ComplianceCase.id == case_id,
            ComplianceCase.tenant_id == tenant_id,
            ComplianceCase.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_cases_for_worker(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> list[ComplianceCase]:
    result = await db.execute(
        select(ComplianceCase)
        .where(
            ComplianceCase.tenant_id == tenant_id,
            ComplianceCase.worker_id == worker_id,
            ComplianceCase.is_deleted == False,
        )
        .order_by(ComplianceCase.created_at.desc())
    )
    return list(result.scalars().all())


async def evaluate_worker_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    worker_id: uuid.UUID,
    rule_key: str,
) -> ComplianceCase:
    worker = await _validate_worker_in_tenant(db, tenant_id, worker_id)
    rule = await get_rule_by_country_and_key(
        db, tenant_id, worker.country, rule_key
    )
    evaluation_status = classify_rule_value(rule)

    existing = await db.execute(
        select(ComplianceCase).where(
            ComplianceCase.tenant_id == tenant_id,
            ComplianceCase.worker_id == worker_id,
            ComplianceCase.rule_key == rule_key,
            ComplianceCase.is_deleted == False,
            ComplianceCase.status != CaseStatus.RESOLVED,
        )
    )
    case = existing.scalar_one_or_none()
    if case is None:
        case = ComplianceCase(
            tenant_id=tenant_id,
            worker_id=worker_id,
            rule_id=rule.id if rule is not None else None,
            rule_key=rule_key,
            evaluation_status=evaluation_status,
            status=CaseStatus.OPEN,
        )
        db.add(case)
    else:
        case.rule_id = rule.id if rule is not None else None
        case.evaluation_status = evaluation_status

    await db.commit()
    await db.refresh(case)
    return case


async def change_case_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    case_id: uuid.UUID,
    new_status: CaseStatus,
    notes: str | None = None,
) -> ComplianceCase:
    case = await get_case(db, tenant_id, case_id)
    if case is None:
        raise CaseNotFoundError(f"Compliance case {case_id} not found")

    allowed_next = ALLOWED_CASE_TRANSITIONS.get(case.status, set())
    if new_status not in allowed_next:
        raise InvalidTransitionError(
            f"Cannot transition from {case.status.value} to {new_status.value}"
        )

    case.status = new_status
    if notes is not None:
        case.notes = notes

    await db.commit()
    await db.refresh(case)
    return case
