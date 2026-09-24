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
            "full_name": "Worker For Docs",
            "email": email,
            "country": "PK",
            "worker_type": "EMPLOYEE",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_documents_tenant_isolation(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token_a = await _register_owner_and_login(client, "tenant-a-docs")
    _, token_b = await _register_owner_and_login(client, "tenant-b-docs")

    worker_a_id = await _create_worker(client, token_a, "worker-a@tenant-a-docs.com")

    create_doc = await client.post(
        "/api/v1/documents",
        json={"worker_id": worker_a_id, "document_type": "PASSPORT"},
        headers=_auth_headers(token_a),
    )
    assert create_doc.status_code == 201, create_doc.text
    document_id = create_doc.json()["id"]

    get_as_owner = await client.get(
        f"/api/v1/documents/{document_id}",
        headers=_auth_headers(token_a),
    )
    assert get_as_owner.status_code == 200

    get_cross_tenant = await client.get(
        f"/api/v1/documents/{document_id}",
        headers=_auth_headers(token_b),
    )
    assert get_cross_tenant.status_code == 404
    assert get_cross_tenant.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    cross_tenant_create_attempt = await client.post(
        "/api/v1/documents",
        json={"worker_id": worker_a_id, "document_type": "VISA"},
        headers=_auth_headers(token_b),
    )
    assert cross_tenant_create_attempt.status_code == 422
    assert cross_tenant_create_attempt.json()["error"]["code"] == "INVALID_WORKER"

    list_cross_tenant = await client.get(
        f"/api/v1/documents/worker/{worker_a_id}",
        headers=_auth_headers(token_b),
    )
    assert list_cross_tenant.status_code == 200
    assert list_cross_tenant.json() == []


@pytest.mark.asyncio
async def test_documents_storage_not_configured(client):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")

    _, token = await _register_owner_and_login(client, "tenant-storage")
    worker_id = await _create_worker(client, token, "worker@tenant-storage.com")

    create_doc = await client.post(
        "/api/v1/documents",
        json={"worker_id": worker_id, "document_type": "PASSPORT"},
        headers=_auth_headers(token),
    )
    assert create_doc.status_code == 201
    document_id = create_doc.json()["id"]

    upload_init = await client.post(
        f"/api/v1/documents/{document_id}/upload-init",
        json={
            "file_name": "passport.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1024,
        },
        headers=_auth_headers(token),
    )
    assert upload_init.status_code == 501
    assert upload_init.json()["error"]["code"] == "STORAGE_NOT_CONFIGURED"
