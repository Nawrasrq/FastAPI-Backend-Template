"""
Tests for user endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models import User


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test getting current user profile."""
    response = await client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == test_user.email
    assert data["data"]["first_name"] == test_user.first_name
    assert data["data"]["last_name"] == test_user.last_name


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without auth fails."""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_current_user(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test updating current user profile."""
    response = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={
            "first_name": "Updated",
            "last_name": "Name",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["first_name"] == "Updated"
    assert data["data"]["last_name"] == "Name"


@pytest.mark.asyncio
async def test_update_current_user_partial(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test partial update of current user profile."""
    response = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={
            "first_name": "OnlyFirst",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["first_name"] == "OnlyFirst"
    assert data["data"]["last_name"] == test_user.last_name  # Unchanged


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test changing password."""
    response = await client.post(
        "/api/v1/users/me/change-password",
        headers=auth_headers,
        json={
            "old_password": "TestPassword123!",
            "new_password": "NewPassword456!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify new password works
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "NewPassword456!",
        },
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_old(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test changing password with wrong old password fails."""
    response = await client.post(
        "/api/v1/users/me/change-password",
        headers=auth_headers,
        json={
            "old_password": "WrongPassword123!",
            "new_password": "NewPassword456!",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_current_user(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test deleting current user account."""
    response = await client.delete("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify user can't login anymore
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "TestPassword123!",
        },
    )
    assert login_response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_by_public_id(client: AsyncClient, test_user: User):
    """Test getting user by public ID."""
    response = await client.get(f"/api/v1/users/{test_user.public_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_user_by_invalid_public_id(client: AsyncClient):
    """Test getting user by invalid public ID fails."""
    response = await client.get("/api/v1/users/invalid-uuid")

    assert response.status_code == 404
