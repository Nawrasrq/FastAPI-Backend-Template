"""
Item service for item management operations.

This module provides the async service layer for item CRUD operations.
"""

import logging

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.item import Item, ItemStatus
from app.repositories.item_repository import ItemRepository
from app.schemas.common_schemas import PaginationMeta
from app.schemas.item_schemas import ItemCreate, ItemUpdate

logger = logging.getLogger(__name__)


class ItemService:
    """
    Async item management service.

    Provides business logic for item CRUD operations including
    ownership validation and pagination.

    Parameters
    ----------
    item_repo : ItemRepository
        Item repository instance (injected)
    """

    def __init__(self, item_repo: ItemRepository):
        """
        Initialize ItemService with repository.

        Parameters
        ----------
        item_repo : ItemRepository
            Repository for item operations
        """
        self.item_repo = item_repo

    # MARK: Read
    async def get_by_id(self, item_id: int) -> Item:
        """
        Get item by internal ID.

        Parameters
        ----------
        item_id : int
            Internal item ID

        Returns
        -------
        Item
            Item instance

        Raises
        ------
        NotFoundError
            If item not found
        """
        item = await self.item_repo.get_by_id(item_id)
        if not item or item.is_deleted:
            raise NotFoundError(message="Item not found", resource="Item")
        return item

    async def get_by_public_id(self, public_id: str) -> Item:
        """
        Get item by public ID (UUID).

        Parameters
        ----------
        public_id : str
            Public UUID identifier

        Returns
        -------
        Item
            Item instance

        Raises
        ------
        NotFoundError
            If item not found
        """
        item = await self.item_repo.get_by_public_id(public_id)
        if not item:
            raise NotFoundError(message="Item not found", resource="Item")
        return item

    async def list_items(
        self,
        page: int = 1,
        per_page: int = 20,
        status: ItemStatus | None = None,
    ) -> tuple[list[Item], PaginationMeta]:
        """
        Get paginated list of items.

        Parameters
        ----------
        page : int
            Page number (1-indexed)
        per_page : int
            Items per page
        status : ItemStatus | None
            Filter by status

        Returns
        -------
        tuple[list[Item], PaginationMeta]
            Items and pagination metadata
        """
        skip = (page - 1) * per_page
        items, total = await self.item_repo.get_paginated(skip=skip, limit=per_page, status=status)

        pagination = PaginationMeta.create(total=total, page=page, per_page=per_page)
        return items, pagination

    async def get_user_items(
        self,
        owner_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Item], int]:
        """
        Get items owned by a specific user.

        Parameters
        ----------
        owner_id : int
            User ID of the owner
        page : int
            Page number (1-indexed)
        per_page : int
            Items per page

        Returns
        -------
        tuple[list[Item], int]
            Items and total count
        """
        skip = (page - 1) * per_page
        items = await self.item_repo.get_by_owner(owner_id=owner_id, skip=skip, limit=per_page)
        # For simplicity, we're not returning total here
        # In a real app, you'd add a count query to the repository
        return items, len(items)

    async def search(self, query: str, limit: int = 50) -> list[Item]:
        """
        Search items by name.

        Parameters
        ----------
        query : str
            Search query
        limit : int
            Maximum results

        Returns
        -------
        list[Item]
            Matching items
        """
        return await self.item_repo.search_by_name(query=query, limit=limit)

    # MARK: Create
    async def create_item(self, data: ItemCreate, owner_id: int) -> Item:
        """
        Create a new item.

        Parameters
        ----------
        data : ItemCreate
            Item creation data
        owner_id : int
            User ID of the owner

        Returns
        -------
        Item
            Created item instance
        """
        item = await self.item_repo.create_item(
            name=data.name,
            description=data.description,
            status=data.status,
            owner_id=owner_id,
        )
        await self.item_repo.commit()

        logger.info(f"Created item '{item.name}' (ID: {item.id}) for owner {owner_id}")
        return item

    # MARK: Update
    async def update_item(
        self,
        public_id: str,
        data: ItemUpdate,
        user_id: int | None = None,
    ) -> Item:
        """
        Update an existing item.

        Parameters
        ----------
        public_id : str
            Item public ID
        data : ItemUpdate
            Update data
        user_id : int | None
            If provided, verify ownership

        Returns
        -------
        Item
            Updated item instance

        Raises
        ------
        NotFoundError
            If item not found
        ForbiddenError
            If user doesn't own the item
        """
        item = await self.get_by_public_id(public_id)

        # Verify ownership if user_id provided
        if user_id is not None and item.owner_id != user_id:
            raise ForbiddenError(message="You don't have permission to update this item")

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(item, field) and value is not None:
                setattr(item, field, value)

        await self.item_repo.flush()
        await self.item_repo.commit()

        logger.info(f"Updated item {public_id}")
        return item

    # MARK: Delete
    async def delete_item(
        self,
        public_id: str,
        user_id: int | None = None,
    ) -> bool:
        """
        Soft delete an item.

        Parameters
        ----------
        public_id : str
            Item public ID
        user_id : int | None
            If provided, verify ownership

        Returns
        -------
        bool
            True if deleted

        Raises
        ------
        NotFoundError
            If item not found
        ForbiddenError
            If user doesn't own the item
        """
        item = await self.get_by_public_id(public_id)

        # Verify ownership if user_id provided
        if user_id is not None and item.owner_id != user_id:
            raise ForbiddenError(message="You don't have permission to delete this item")

        item.soft_delete()
        await self.item_repo.flush()
        await self.item_repo.commit()

        logger.info(f"Soft deleted item {public_id}")
        return True

    # MARK: Status Management
    async def activate_item(self, public_id: str, user_id: int | None = None) -> Item:
        """
        Set item status to ACTIVE.

        Parameters
        ----------
        public_id : str
            Item public ID
        user_id : int | None
            If provided, verify ownership

        Returns
        -------
        Item
            Updated item
        """
        item = await self.get_by_public_id(public_id)

        if user_id is not None and item.owner_id != user_id:
            raise ForbiddenError(message="You don't have permission to modify this item")

        item.activate()
        await self.item_repo.flush()
        await self.item_repo.commit()

        logger.info(f"Activated item {public_id}")
        return item

    async def archive_item(self, public_id: str, user_id: int | None = None) -> Item:
        """
        Set item status to ARCHIVED.

        Parameters
        ----------
        public_id : str
            Item public ID
        user_id : int | None
            If provided, verify ownership

        Returns
        -------
        Item
            Updated item
        """
        item = await self.get_by_public_id(public_id)

        if user_id is not None and item.owner_id != user_id:
            raise ForbiddenError(message="You don't have permission to modify this item")

        item.archive()
        await self.item_repo.flush()
        await self.item_repo.commit()

        logger.info(f"Archived item {public_id}")
        return item
