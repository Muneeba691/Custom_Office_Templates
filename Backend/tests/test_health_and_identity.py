import uuid

import pytest
from sqlalchemy import text

from app.core.database import engine


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Cross-Border Workforce OS"


@pytest.mark.asyncio
async def test_missing_bearer_token_on_me(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_tenant_register_login_and_me(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")
    slug = f"acme-{uuid.uuid4().hex[:8]}"
    create_tenant = await client.post(
        "/api/v1/tenants",
        json={"name": "Acme Corp", "slug": slug},
    )
    assert create_tenant.status_code == 201, create_tenant.text
    tenant_body = create_tenant.json()
    assert tenant_body["slug"] == slug
    assert tenant_body["status"] == "ACTIVE"

    duplicate = await client.post(
        "/api/v1/tenants",
        json={"name": "Acme Duplicate", "slug": slug},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "SLUG_TAKEN"

    first = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": slug,
            "email": "owner@example.com",
            "password": "password123",
            "full_name": "Owner One",
        },
    )
    assert first.status_code == 201, first.text
    assert first.json()["role"] == "OWNER"

    second = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": slug,
            "email": "worker@example.com",
            "password": "password123",
            "full_name": "Worker Two",
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["role"] == "WORKER"

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": slug,
            "email": "owner@example.com",
            "password": "password123",
        },
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": slug,
            "email": "owner@example.com",
            "password": "wrong-password",
        },
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "INVALID_CREDENTIALS"

    refresh_as_access = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert refresh_as_access.status_code == 401
    assert refresh_as_access.json()["error"]["code"] == "INVALID_TOKEN_TYPE"

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200, me.text
    me_body = me.json()
    assert me_body["email"] == "owner@example.com"
    assert me_body["role"] == "OWNER"
    assert "hashed_password" not in me_body
