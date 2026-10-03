import uuid

import pytest
from sqlalchemy import text

from app.core.database import engine


async def _register_owner_and_login(client, tenant_name: str):
    slug = f"{tenant_name}-{uuid.uuid4().hex[:8]}"
    create_tenant = await client.post(
        "/api/v1/tenants",
        json={"name": tenant_name, "slug": slug},
    )
    assert create_tenant.status_code == 201, create_tenant.text

    register = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": slug,
            "email": f"owner-{uuid.uuid4().hex[:6]}@example.com",
            "password": "password123",
            "full_name": "Owner",
        },
    )
    assert register.status_code == 201, register.text
    email = register.json()["email"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": slug, "email": email, "password": "password123"},
    )
    assert login.status_code == 200, login.text
    return slug, login.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_worker(client, token: str, email: str, country: str = "PK") -> str:
    resp = await client.post(
        "/api/v1/workforce",
        json={
            "full_name": "Worker For Compliance",
            "email": email,
            "country": country,
            "worker_type": "EMPLOYEE",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_compliance_tenant_isolation(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token_a = await _register_owner_and_login(client, "tenant-a-cply")
    _, token_b = await _register_owner_and_login(client, "tenant-b-cply")

    worker_a_id = await _create_worker(client, token_a, "worker-a@tenant-a-cply.com")

    create_rule = await client.post(
        "/api/v1/compliance/rules",
        json={
            "country": "PK",
            "rule_key": "MIN_WAGE",
            "rule_value": {"value": 32000, "currency": "PKR"},
        },
        headers=_auth_headers(token_a),
    )
    assert create_rule.status_code == 201, create_rule.text
    rule_id = create_rule.json()["id"]

    get_rule_cross = await client.get(
        f"/api/v1/compliance/rules/{rule_id}",
        headers=_auth_headers(token_b),
    )
    assert get_rule_cross.status_code == 404
    assert get_rule_cross.json()["error"]["code"] == "RULE_NOT_FOUND"

    patch_rule_cross = await client.patch(
        f"/api/v1/compliance/rules/{rule_id}",
        json={"is_active": False},
        headers=_auth_headers(token_b),
    )
    assert patch_rule_cross.status_code == 404

    delete_rule_cross = await client.delete(
        f"/api/v1/compliance/rules/{rule_id}",
        headers=_auth_headers(token_b),
    )
    assert delete_rule_cross.status_code == 404

    list_rules_b = await client.get(
        "/api/v1/compliance/rules",
        headers=_auth_headers(token_b),
    )
    assert list_rules_b.status_code == 200
    assert list_rules_b.json() == []

    evaluate_a = await client.post(
        "/api/v1/compliance/evaluate",
        json={"worker_id": worker_a_id, "rule_key": "MIN_WAGE"},
        headers=_auth_headers(token_a),
    )
    assert evaluate_a.status_code == 201, evaluate_a.text
    case_id = evaluate_a.json()["id"]
    assert evaluate_a.json()["evaluation_status"] == "KNOWN"

    get_case_cross = await client.get(
        f"/api/v1/compliance/cases/{case_id}",
        headers=_auth_headers(token_b),
    )
    assert get_case_cross.status_code == 404
    assert get_case_cross.json()["error"]["code"] == "CASE_NOT_FOUND"

    status_cross = await client.patch(
        f"/api/v1/compliance/cases/{case_id}/status",
        json={"new_status": "RESOLVED"},
        headers=_auth_headers(token_b),
    )
    assert status_cross.status_code == 404

    evaluate_cross_worker = await client.post(
        "/api/v1/compliance/evaluate",
        json={"worker_id": worker_a_id, "rule_key": "MIN_WAGE"},
        headers=_auth_headers(token_b),
    )
    assert evaluate_cross_worker.status_code == 422
    assert evaluate_cross_worker.json()["error"]["code"] == "INVALID_WORKER"

    list_cases_b = await client.get(
        f"/api/v1/compliance/cases/worker/{worker_a_id}",
        headers=_auth_headers(token_b),
    )
    assert list_cases_b.status_code == 200
    assert list_cases_b.json() == []


@pytest.mark.asyncio
async def test_compliance_evaluate_statuses_and_transitions(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token = await _register_owner_and_login(client, "tenant-cply-eval")
    worker_id = await _create_worker(client, token, "worker@tenant-cply-eval.com", country="US")

    known_rule = await client.post(
        "/api/v1/compliance/rules",
        json={
            "country": "US",
            "rule_key": "MAX_WORK_HOURS",
            "rule_value": {"value": 40, "unit": "hours_per_week"},
        },
        headers=_auth_headers(token),
    )
    assert known_rule.status_code == 201, known_rule.text

    ambiguous_rule = await client.post(
        "/api/v1/compliance/rules",
        json={
            "country": "US",
            "rule_key": "OVERTIME_PREMIUM",
            "rule_value": {"ambiguous": True, "notes": "Varies by state"},
        },
        headers=_auth_headers(token),
    )
    assert ambiguous_rule.status_code == 201, ambiguous_rule.text

    known_case = await client.post(
        "/api/v1/compliance/evaluate",
        json={"worker_id": worker_id, "rule_key": "MAX_WORK_HOURS"},
        headers=_auth_headers(token),
    )
    assert known_case.status_code == 201, known_case.text
    assert known_case.json()["evaluation_status"] == "KNOWN"
    assert known_case.json()["status"] == "OPEN"

    review_case = await client.post(
        "/api/v1/compliance/evaluate",
        json={"worker_id": worker_id, "rule_key": "OVERTIME_PREMIUM"},
        headers=_auth_headers(token),
    )
    assert review_case.status_code == 201
    assert review_case.json()["evaluation_status"] == "REVIEW_REQUIRED"

    unknown_case = await client.post(
        "/api/v1/compliance/evaluate",
        json={"worker_id": worker_id, "rule_key": "STATUTORY_HOLIDAYS"},
        headers=_auth_headers(token),
    )
    assert unknown_case.status_code == 201
    assert unknown_case.json()["evaluation_status"] == "UNKNOWN"
    assert unknown_case.json()["rule_id"] is None

    case_id = known_case.json()["id"]
    invalid_jump = await client.patch(
        f"/api/v1/compliance/cases/{case_id}/status",
        json={"new_status": "OPEN"},
        headers=_auth_headers(token),
    )
    assert invalid_jump.status_code == 409
    assert invalid_jump.json()["error"]["code"] == "INVALID_TRANSITION"

    valid_step = await client.patch(
        f"/api/v1/compliance/cases/{case_id}/status",
        json={"new_status": "UNDER_REVIEW", "notes": "Checking hours policy"},
        headers=_auth_headers(token),
    )
    assert valid_step.status_code == 200
    assert valid_step.json()["status"] == "UNDER_REVIEW"


@pytest.mark.asyncio
async def test_compliance_rbac_worker_role_cannot_create_rule(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    slug, _owner_token = await _register_owner_and_login(client, "tenant-cply-rbac")

    worker_register = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": slug,
            "email": "plain@cply-rbac.com",
            "password": "password123",
            "full_name": "Plain Worker",
        },
    )
    assert worker_register.json()["role"] == "WORKER"

    worker_login = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": slug,
            "email": "plain@cply-rbac.com",
            "password": "password123",
        },
    )
    worker_token = worker_login.json()["access_token"]

    attempt_create = await client.post(
        "/api/v1/compliance/rules",
        json={
            "country": "PK",
            "rule_key": "MIN_WAGE",
            "rule_value": {"value": 1},
        },
        headers=_auth_headers(worker_token),
    )
    assert attempt_create.status_code == 403
