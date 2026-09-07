import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://workforce:workforce@localhost:5432/workforce")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-do-not-use-in-production")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
