"""
Item router for item CRUD operations.

This module provides FastAPI routes for item management.
"""

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUserId, OptionalUser
from app.core.exceptions import ValidationError
from app.core.responses import success_response
from app.db.session import get_db
from app.models.item import ItemStatus
from app.repositories.item_repository import ItemRepository
from app.schemas.item_schemas import ItemCreate, ItemResponse, ItemUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["Items"])


# MARK: Dependencies
async def get_item_service(db: AsyncSession = Depends(get_db)):
    """Dependency to create ItemService with injected repository."""
    from app.services.item_service import ItemService

    return ItemService(item_repo=ItemRepository(db))


# MARK: Routes
@router.get(
    "",
    response_model=None,
    summary="List items",
    description="Get a paginated list of items with optional status filter.",
)
async def list_items(
    service=Depends(get_item_service),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(default=None, description="Filter by status"),
):
    """
    List items with pagination.

    Parameters
    ----------
    page : int
        Page number (1-indexed)
    per_page : int
        Items per page (max 100)
    status : str | None
        Optional status filter (draft, active, archived)

    Returns
    -------
    dict
        Success response with items and pagination
    """
    item_status = None
    if status:
        try:
            item_status = ItemStatus(status)
        except ValueError:
            raise ValidationError(
                message=f"Invalid status: {status}. Valid values: draft, active, archived"
            ) from None

    items, pagination = await service.list_items(page=page, per_page=per_page, status=item_status)

    items_data = [ItemResponse.model_validate(item).model_dump() for item in items]
    return success_response(
        {
            "items": items_data,
            "pagination": pagination.model_dump(),
        }
    )


@router.get(
    "/my",
    response_model=None,
    summary="List my items",
    description="Get items owned by the current user.",
)
async def list_my_items(
    user_id: CurrentUserId,
    service=Depends(get_item_service),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """
    List items owned by the current user.

    Requires authentication.

    Parameters
    ----------
    page : int
        Page number
    per_page : int
        Items per page

    Returns
    -------
    dict
        Success response with items
    """
    items, total = await service.get_user_items(owner_id=user_id, page=page, per_page=per_page)

    items_data = [ItemResponse.model_validate(item).model_dump() for item in items]
    return success_response({"items": items_data, "count": len(items_data)})


@router.get(
    "/search",
    response_model=None,
    summary="Search items",
    description="Search items by name.",
)
async def search_items(
    q: str = Query(min_length=1, description="Search query"),
    limit: int = Query(default=50, ge=1, le=100, description="Max results"),
    service=Depends(get_item_service),
):
    """
    Search items by name.

    Parameters
    ----------
    q : str
        Search query
    limit : int
        Maximum results

    Returns
    -------
    dict
        Success response with matching items
    """
    items = await service.search(query=q, limit=limit)
    items_data = [ItemResponse.model_validate(item).model_dump() for item in items]
    return success_response({"items": items_data, "count": len(items_data)})


@router.get(
    "/{public_id}",
    response_model=None,
    summary="Get item",
    description="Get a single item by public ID.",
)
async def get_item(
    public_id: str,
    service=Depends(get_item_service),
    current_user: OptionalUser = None,
):
    """
    Get item by public ID.

    Parameters
    ----------
    public_id : str
        Item's public UUID

    Returns
    -------
    dict
        Success response with item data
    """
    item = await service.get_by_public_id(public_id)
    item_data = ItemResponse.model_validate(item).model_dump()

    # Add ownership info if user is authenticated
    if current_user:
        item_data["is_owner"] = item.owner_id == int(current_user.sub)

    return success_response(item_data)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    summary="Create item",
    description="Create a new item. Requires authentication.",
)
async def create_item(
    data: ItemCreate,
    user_id: CurrentUserId,
    service=Depends(get_item_service),
):
    """
    Create a new item.

    Requires authentication. The current user becomes the owner.

    Parameters
    ----------
    data : ItemCreate
        Item creation data

    Returns
    -------
    dict
        Success response with created item
    """
    item = await service.create_item(data, owner_id=user_id)
    logger.info(f"Item created: {item.public_id}")
    return success_response(ItemResponse.model_validate(item).model_dump())


@router.patch(
    "/{public_id}",
    response_model=None,
    summary="Update item",
    description="Update an existing item. Requires ownership.",
)
async def update_item(
    public_id: str,
    data: ItemUpdate,
    user_id: CurrentUserId,
    service=Depends(get_item_service),
):
    """
    Update an existing item.

    Requires authentication and ownership.

    Parameters
    ----------
    public_id : str
        Item's public UUID
    data : ItemUpdate
        Update data

    Returns
    -------
    dict
        Success response with updated item
    """
    item = await service.update_item(public_id, data, user_id=user_id)
    logger.info(f"Item updated: {public_id}")
    return success_response(ItemResponse.model_validate(item).model_dump())


@router.delete(
    "/{public_id}",
    response_model=None,
    summary="Delete item",
    description="Soft delete an item. Requires ownership.",
)
async def delete_item(
    public_id: str,
    user_id: CurrentUserId,
    service=Depends(get_item_service),
):
    """
    Delete an item (soft delete).

    Requires authentication and ownership.

    Parameters
    ----------
    public_id : str
        Item's public UUID

    Returns
    -------
    dict
        Success response
    """
    await service.delete_item(public_id, user_id=user_id)
    logger.info(f"Item deleted: {public_id}")
    return success_response({"message": "Item deleted successfully"})


@router.post(
    "/{public_id}/activate",
    response_model=None,
    summary="Activate item",
    description="Set item status to active. Requires ownership.",
)
async def activate_item(
    public_id: str,
    user_id: CurrentUserId,
    service=Depends(get_item_service),
):
    """
    Activate an item.

    Requires authentication and ownership.

    Returns
    -------
    dict
        Success response with updated item
    """
    item = await service.activate_item(public_id, user_id=user_id)
    return success_response(ItemResponse.model_validate(item).model_dump())


@router.post(
    "/{public_id}/archive",
    response_model=None,
    summary="Archive item",
    description="Set item status to archived. Requires ownership.",
)
async def archive_item(
    public_id: str,
    user_id: CurrentUserId,
    service=Depends(get_item_service),
):
    """
    Archive an item.

    Requires authentication and ownership.

    Returns
    -------
    dict
        Success response with updated item
    """
    item = await service.archive_item(public_id, user_id=user_id)
    return success_response(ItemResponse.model_validate(item).model_dump())
