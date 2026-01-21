"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models import User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "NewPassword123!",
            "first_name": "New",
            "last_name": "User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    """Test registration with existing email fails."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,  # Already exists
            "password": "NewPassword123!",
            "first_name": "New",
            "last_name": "User",
        },
    )

    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert "already exists" in data["message"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test registration with weak password fails."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "weak",  # Too weak
            "first_name": "New",
            "last_name": "User",
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    """Test login with non-existent email."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user: User):
    """Test login with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_refresh_tokens(client: AsyncClient, test_user: User):
    """Test token refresh."""
    # First login to get tokens
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
        },
    )
    tokens = login_response.json()["data"]

    # Now refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    # New tokens should be different
    assert data["data"]["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user: User):
    """Test logout revokes refresh token."""
    # First login to get tokens
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
        },
    )
    tokens = login_response.json()["data"]

    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Try to use the old refresh token - should fail
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_all(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test logout from all devices."""
    response = await client.post(
        "/api/v1/auth/logout-all",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tokens_revoked" in data["data"]
