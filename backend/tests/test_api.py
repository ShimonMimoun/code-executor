"""Tests for the Code Executor API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models import ExecutionStatus


@pytest.fixture
def api_key():
    return "dev-api-key-change-me"


@pytest.fixture
def auth_headers(api_key):
    return {"X-API-Key": api_key}


@pytest.mark.asyncio
async def test_root():
    """Root endpoint returns app info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Code Executor Platform"
    assert "version" in data


@pytest.mark.asyncio
async def test_languages():
    """Languages endpoint returns supported languages."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/languages")
    assert res.status_code == 200
    languages = res.json()
    assert len(languages) >= 4
    names = [l["name"] for l in languages]
    assert "python" in names
    assert "javascript" in names
    assert "go" in names
    assert "bash" in names


@pytest.mark.asyncio
async def test_execute_requires_auth():
    """Execute endpoint requires API key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/execute",
            json={"code": "print('hi')", "language": "python"},
        )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_execute_invalid_key():
    """Execute endpoint rejects invalid API key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/execute",
            json={"code": "print('hi')", "language": "python"},
            headers={"X-API-Key": "invalid-key"},
        )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_execute_unsupported_language(auth_headers):
    """Execute rejects unsupported languages."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/execute",
            json={"code": "print('hi')", "language": "rust"},
            headers=auth_headers,
        )
    assert res.status_code == 400
    assert "Unsupported language" in res.json()["detail"]


@pytest.mark.asyncio
async def test_execute_empty_code(auth_headers):
    """Execute rejects empty code."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/execute",
            json={"code": "", "language": "python"},
            headers=auth_headers,
        )
    assert res.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_execution_not_found(auth_headers):
    """Getting a non-existent execution returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/executions/non-existent-id",
            headers=auth_headers,
        )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_health():
    """Health endpoint returns status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "version" in data
