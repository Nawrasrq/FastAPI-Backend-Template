"""
Tests for item endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Item, User
from app.models.item import ItemStatus


@pytest.fixture
async def test_item(db_session: AsyncSession, test_user: User) -> Item:
    """Create a test item owned by test_user."""
    item = Item(
        name="Test Item",
        description="A test item description",
        status=ItemStatus.DRAFT,
        owner_id=test_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_list_items(client: AsyncClient, test_item: Item):
    """Test listing items."""
    response = await client.get("/api/v1/items")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "items" in data["data"]
    assert "pagination" in data["data"]
    assert len(data["data"]["items"]) >= 1


@pytest.mark.asyncio
async def test_list_items_with_status_filter(client: AsyncClient, test_item: Item):
    """Test listing items with status filter."""
    response = await client.get("/api/v1/items?status=draft")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert all(item["status"] == "draft" for item in data["data"]["items"])


@pytest.mark.asyncio
async def test_list_items_invalid_status(client: AsyncClient):
    """Test listing items with invalid status returns error."""
    response = await client.get("/api/v1/items?status=invalid")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_item(client: AsyncClient, test_item: Item):
    """Test getting a single item."""
    response = await client.get(f"/api/v1/items/{test_item.public_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == test_item.name
    assert data["data"]["public_id"] == test_item.public_id


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    """Test getting non-existent item returns 404."""
    response = await client.get("/api/v1/items/non-existent-id")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_item(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test creating a new item."""
    response = await client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "name": "New Item",
            "description": "A new item",
            "status": "draft",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "New Item"
    assert "public_id" in data["data"]


@pytest.mark.asyncio
async def test_create_item_unauthorized(client: AsyncClient):
    """Test creating item without auth fails."""
    response = await client.post(
        "/api/v1/items",
        json={
            "name": "New Item",
            "description": "A new item",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_item(client: AsyncClient, test_item: Item, auth_headers: dict):
    """Test updating an item."""
    response = await client.patch(
        f"/api/v1/items/{test_item.public_id}",
        headers=auth_headers,
        json={
            "name": "Updated Item Name",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Updated Item Name"


@pytest.mark.asyncio
async def test_update_item_not_owner(
    client: AsyncClient,
    test_item: Item,
    admin_user: User,
    admin_auth_headers: dict,
):
    """Test updating item by non-owner fails."""
    response = await client.patch(
        f"/api/v1/items/{test_item.public_id}",
        headers=admin_auth_headers,
        json={
            "name": "Should Not Work",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient, test_item: Item, auth_headers: dict):
    """Test deleting an item."""
    response = await client.delete(
        f"/api/v1/items/{test_item.public_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify item is deleted (soft delete)
    get_response = await client.get(f"/api/v1/items/{test_item.public_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_activate_item(client: AsyncClient, test_item: Item, auth_headers: dict):
    """Test activating an item."""
    response = await client.post(
        f"/api/v1/items/{test_item.public_id}/activate",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_archive_item(client: AsyncClient, test_item: Item, auth_headers: dict):
    """Test archiving an item."""
    response = await client.post(
        f"/api/v1/items/{test_item.public_id}/archive",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "archived"


@pytest.mark.asyncio
async def test_search_items(client: AsyncClient, test_item: Item):
    """Test searching items by name."""
    response = await client.get("/api/v1/items/search?q=Test")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 1
    assert any("Test" in item["name"] for item in data["data"]["items"])


@pytest.mark.asyncio
async def test_list_my_items(client: AsyncClient, test_item: Item, auth_headers: dict):
    """Test listing items owned by current user."""
    response = await client.get("/api/v1/items/my", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 1
