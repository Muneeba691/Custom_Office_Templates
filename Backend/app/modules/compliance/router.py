import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.modules.compliance.schemas import (
    ComplianceCaseOut,
    ComplianceCaseStatusChange,
    ComplianceEvaluateRequest,
    ComplianceRuleCreate,
    ComplianceRuleOut,
    ComplianceRuleUpdate,
)
from app.modules.compliance.service import (
    CaseNotFoundError,
    InvalidTransitionError,
    RuleAlreadyExistsError,
    RuleNotFoundError,
    WorkerNotInTenantError,
    change_case_status,
    create_rule,
    evaluate_worker_rule,
    get_case,
    get_rule,
    list_cases_for_worker,
    list_rules,
    soft_delete_rule,
    update_rule,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])

WRITE_ROLES = ("OWNER", "ADMIN", "COMPLIANCE", "LEGAL", "HR")
READ_ROLES = ("OWNER", "ADMIN", "COMPLIANCE", "LEGAL", "HR", "AUDITOR")


@router.post(
    "/rules",
    response_model=ComplianceRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_rule_endpoint(
    payload: ComplianceRuleCreate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        rule = await create_rule(
            db,
            tenant_id=ctx.tenant_id,
            country=payload.country,
            rule_key=payload.rule_key,
            rule_value=payload.rule_value,
            is_active=payload.is_active,
        )
    except RuleAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "RULE_ALREADY_EXISTS", "message": str(exc)}},
        )
    return rule


@router.get(
    "/rules",
    response_model=list[ComplianceRuleOut],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_rules_endpoint(
    country: str | None = Query(default=None),
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    country_filter = country.strip().upper() if country else None
    return await list_rules(db, ctx.tenant_id, country=country_filter)


@router.get(
    "/rules/{rule_id}",
    response_model=ComplianceRuleOut,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_rule_endpoint(
    rule_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    rule = await get_rule(db, ctx.tenant_id, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RULE_NOT_FOUND", "message": "Compliance rule not found"}},
        )
    return rule


@router.patch(
    "/rules/{rule_id}",
    response_model=ComplianceRuleOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def update_rule_endpoint(
    rule_id: uuid.UUID,
    payload: ComplianceRuleUpdate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        rule = await update_rule(
            db,
            ctx.tenant_id,
            rule_id,
            **payload.model_dump(exclude_unset=True),
        )
    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RULE_NOT_FOUND", "message": "Compliance rule not found"}},
        )
    return rule


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def delete_rule_endpoint(
    rule_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        await soft_delete_rule(db, ctx.tenant_id, rule_id)
    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RULE_NOT_FOUND", "message": "Compliance rule not found"}},
        )


@router.post(
    "/evaluate",
    response_model=ComplianceCaseOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def evaluate_endpoint(
    payload: ComplianceEvaluateRequest,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        case = await evaluate_worker_rule(
            db,
            tenant_id=ctx.tenant_id,
            worker_id=payload.worker_id,
            rule_key=payload.rule_key,
        )
    except WorkerNotInTenantError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_WORKER", "message": str(exc)}},
        )
    return case


@router.get(
    "/cases/worker/{worker_id}",
    response_model=list[ComplianceCaseOut],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_worker_cases_endpoint(
    worker_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_cases_for_worker(db, ctx.tenant_id, worker_id)


@router.get(
    "/cases/{case_id}",
    response_model=ComplianceCaseOut,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_case_endpoint(
    case_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    case = await get_case(db, ctx.tenant_id, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "CASE_NOT_FOUND", "message": "Compliance case not found"}},
        )
    return case


@router.patch(
    "/cases/{case_id}/status",
    response_model=ComplianceCaseOut,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def change_case_status_endpoint(
    case_id: uuid.UUID,
    payload: ComplianceCaseStatusChange,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        case = await change_case_status(
            db,
            ctx.tenant_id,
            case_id,
            new_status=payload.new_status,
            notes=payload.notes,
        )
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "CASE_NOT_FOUND", "message": "Compliance case not found"}},
        )
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(exc)}},
        )
    return case
