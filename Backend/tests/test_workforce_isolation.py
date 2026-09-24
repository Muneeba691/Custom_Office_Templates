import uuid
import pytest
from app.core.database import engine
from sqlalchemy import text

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
    assert register.json()["role"] == "OWNER"
    email = register.json()["email"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": slug, "email": email, "password": "password123"},
    )
    assert login.status_code == 200, login.text
    return slug, login.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_workforce_tenant_isolation(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token_a = await _register_owner_and_login(client, "tenant-a")
    _, token_b = await _register_owner_and_login(client, "tenant-b")

    create_worker = await client.post(
        "/api/v1/workforce",
        json={
            "full_name": "Alice Employee",
            "email": "alice@tenant-a.com",
            "country": "PK",
            "worker_type": "EMPLOYEE",
        },
        headers=_auth_headers(token_a),
    )
    assert create_worker.status_code == 201, create_worker.text
    worker_id = create_worker.json()["id"]

    get_as_owner = await client.get(
        f"/api/v1/workforce/{worker_id}",
        headers=_auth_headers(token_a),
    )
    assert get_as_owner.status_code == 200, get_as_owner.text

    get_cross_tenant = await client.get(
        f"/api/v1/workforce/{worker_id}",
        headers=_auth_headers(token_b),
    )
    assert get_cross_tenant.status_code == 404
    assert get_cross_tenant.json()["error"]["code"] == "WORKER_NOT_FOUND"

    patch_cross_tenant = await client.patch(
        f"/api/v1/workforce/{worker_id}",
        json={"full_name": "Hacked Name"},
        headers=_auth_headers(token_b),
    )
    assert patch_cross_tenant.status_code == 404

    delete_cross_tenant = await client.delete(
        f"/api/v1/workforce/{worker_id}",
        headers=_auth_headers(token_b),
    )
    assert delete_cross_tenant.status_code == 404

    list_as_tenant_b = await client.get(
        "/api/v1/workforce",
        headers=_auth_headers(token_b),
    )
    assert list_as_tenant_b.status_code == 200
    ids_visible_to_b = [w["id"] for w in list_as_tenant_b.json()]
    assert worker_id not in ids_visible_to_b

    confirm_still_intact = await client.get(
        f"/api/v1/workforce/{worker_id}",
        headers=_auth_headers(token_a),
    )
    assert confirm_still_intact.status_code == 200
    assert confirm_still_intact.json()["full_name"] == "Alice Employee"


@pytest.mark.asyncio
async def test_workforce_rbac_worker_role_cannot_create(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    slug = f"tenant-rbac-{uuid.uuid4().hex[:8]}"
    create_tenant = await client.post(
        "/api/v1/tenants",
        json={"name": "RBAC Test", "slug": slug},
    )
    assert create_tenant.status_code == 201

    await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": slug,
            "email": "owner@rbac-test.com",
            "password": "password123",
            "full_name": "Owner",
        },
    )
    worker_register = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": slug,
            "email": "plain@rbac-test.com",
            "password": "password123",
            "full_name": "Plain Worker",
        },
    )
    assert worker_register.json()["role"] == "WORKER"

    worker_login = await client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": slug, "email": "plain@rbac-test.com", "password": "password123"},
    )
    worker_token = worker_login.json()["access_token"]

    attempt_create = await client.post(
        "/api/v1/workforce",
        json={
            "full_name": "Should Not Be Created",
            "email": "nope@tenant.com",
            "country": "PK",
            "worker_type": "EMPLOYEE",
        },
        headers=_auth_headers(worker_token),
    )
    assert attempt_create.status_code == 403
