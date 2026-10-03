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
            "full_name": "Worker For Compensation",
            "email": email,
            "country": "PK",
            "worker_type": "EMPLOYEE",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_compensation_tenant_isolation(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token_a = await _register_owner_and_login(client, "tenant-a-comp")
    _, token_b = await _register_owner_and_login(client, "tenant-b-comp")

    worker_a_id = await _create_worker(client, token_a, "worker-a@tenant-a-comp.com")

    create_record = await client.post(
        "/api/v1/compensation",
        json={
            "worker_id": worker_a_id,
            "compensation_type": "BASE_SALARY",
            "amount": "120000.00",
            "currency": "PKR",
            "frequency": "ANNUAL",
            "effective_date": "2026-01-01",
        },
        headers=_auth_headers(token_a),
    )
    assert create_record.status_code == 201, create_record.text
    record_id = create_record.json()["id"]

    get_cross_tenant = await client.get(
        f"/api/v1/compensation/{record_id}",
        headers=_auth_headers(token_b),
    )
    assert get_cross_tenant.status_code == 404
    assert get_cross_tenant.json()["error"]["code"] == "COMPENSATION_NOT_FOUND"

    patch_cross_tenant = await client.patch(
        f"/api/v1/compensation/{record_id}",
        json={"amount": "1.00"},
        headers=_auth_headers(token_b),
    )
    assert patch_cross_tenant.status_code == 404

    delete_cross_tenant = await client.delete(
        f"/api/v1/compensation/{record_id}",
        headers=_auth_headers(token_b),
    )
    assert delete_cross_tenant.status_code == 404

    cross_tenant_create = await client.post(
        "/api/v1/compensation",
        json={
            "worker_id": worker_a_id,
            "compensation_type": "BONUS",
            "amount": "500.00",
            "currency": "USD",
            "frequency": "ONE_TIME",
            "effective_date": "2026-02-01",
        },
        headers=_auth_headers(token_b),
    )
    assert cross_tenant_create.status_code == 422
    assert cross_tenant_create.json()["error"]["code"] == "INVALID_WORKER"

    list_cross_tenant = await client.get(
        f"/api/v1/compensation/worker/{worker_a_id}",
        headers=_auth_headers(token_b),
    )
    assert list_cross_tenant.status_code == 200
    assert list_cross_tenant.json() == []


@pytest.mark.asyncio
async def test_compensation_rbac_worker_role_cannot_create(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    slug, owner_token = await _register_owner_and_login(client, "tenant-comp-rbac")
    worker_id = await _create_worker(client, owner_token, "hr-worker@comp-rbac.com")

    worker_register = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": slug,
            "email": "plain@comp-rbac.com",
            "password": "password123",
            "full_name": "Plain Worker",
        },
    )
    assert worker_register.json()["role"] == "WORKER"

    worker_login = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": slug,
            "email": "plain@comp-rbac.com",
            "password": "password123",
        },
    )
    worker_token = worker_login.json()["access_token"]

    attempt_create = await client.post(
        "/api/v1/compensation",
        json={
            "worker_id": worker_id,
            "compensation_type": "BASE_SALARY",
            "amount": "1000.00",
            "currency": "USD",
            "frequency": "MONTHLY",
            "effective_date": "2026-01-01",
        },
        headers=_auth_headers(worker_token),
    )
    assert attempt_create.status_code == 403
