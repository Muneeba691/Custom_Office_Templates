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


async def _create_worker(client, token: str, email: str) -> str:
    resp = await client.post(
        "/api/v1/workforce",
        json={
            "full_name": "Worker For Agreements",
            "email": email,
            "country": "PK",
            "worker_type": "EMPLOYEE",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_agreements_tenant_isolation(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token_a = await _register_owner_and_login(client, "tenant-a-agr")
    _, token_b = await _register_owner_and_login(client, "tenant-b-agr")

    worker_a_id = await _create_worker(client, token_a, "worker-a@tenant-a-agr.com")

    create_agreement = await client.post(
        "/api/v1/agreements",
        json={
            "worker_id": worker_a_id,
            "title": "Employment Contract - Alice",
            "agreement_type": "EMPLOYMENT_CONTRACT",
        },
        headers=_auth_headers(token_a),
    )
    assert create_agreement.status_code == 201, create_agreement.text
    agreement_id = create_agreement.json()["id"]
    assert create_agreement.json()["status"] == "DRAFT"

    get_cross_tenant = await client.get(
        f"/api/v1/agreements/{agreement_id}",
        headers=_auth_headers(token_b),
    )
    assert get_cross_tenant.status_code == 404
    assert get_cross_tenant.json()["error"]["code"] == "AGREEMENT_NOT_FOUND"

    cross_tenant_create_attempt = await client.post(
        "/api/v1/agreements",
        json={
            "worker_id": worker_a_id,
            "title": "Should Not Be Created",
            "agreement_type": "NDA",
        },
        headers=_auth_headers(token_b),
    )
    assert cross_tenant_create_attempt.status_code == 422
    assert cross_tenant_create_attempt.json()["error"]["code"] == "INVALID_WORKER"

    status_change_cross_tenant = await client.patch(
        f"/api/v1/agreements/{agreement_id}/status",
        json={"new_status": "TERMINATED", "reason": "attack attempt"},
        headers=_auth_headers(token_b),
    )
    assert status_change_cross_tenant.status_code == 404

    list_cross_tenant = await client.get(
        f"/api/v1/agreements/worker/{worker_a_id}",
        headers=_auth_headers(token_b),
    )
    assert list_cross_tenant.status_code == 200
    assert list_cross_tenant.json() == []


@pytest.mark.asyncio
async def test_agreement_invalid_transition_rejected(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token = await _register_owner_and_login(client, "tenant-transitions")
    worker_id = await _create_worker(client, token, "worker@tenant-transitions.com")

    create_agreement = await client.post(
        "/api/v1/agreements",
        json={
            "worker_id": worker_id,
            "title": "Test Agreement",
            "agreement_type": "NDA",
        },
        headers=_auth_headers(token),
    )
    agreement_id = create_agreement.json()["id"]

    invalid_jump = await client.patch(
        f"/api/v1/agreements/{agreement_id}/status",
        json={"new_status": "ACTIVE"},
        headers=_auth_headers(token),
    )
    assert invalid_jump.status_code == 409
    assert invalid_jump.json()["error"]["code"] == "INVALID_TRANSITION"

    valid_step = await client.patch(
        f"/api/v1/agreements/{agreement_id}/status",
        json={"new_status": "INTERNAL_REVIEW"},
        headers=_auth_headers(token),
    )
    assert valid_step.status_code == 200
    assert valid_step.json()["status"] == "INTERNAL_REVIEW"

    terminate_without_reason = await client.patch(
        f"/api/v1/agreements/{agreement_id}/status",
        json={"new_status": "TERMINATED"},
        headers=_auth_headers(token),
    )
    assert terminate_without_reason.status_code == 422
    assert terminate_without_reason.json()["error"]["code"] == "REASON_REQUIRED"
