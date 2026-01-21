"""
Tests for health check endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test basic health check returns healthy status."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """Test readiness check returns ready status."""
    response = await client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ready"


@pytest.mark.asyncio
async def test_liveness_check(client: AsyncClient):
    """Test liveness check returns alive status."""
    response = await client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "alive"
