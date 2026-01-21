"""
Item repository for async database operations.

This module provides data access methods specific to the Item model.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item, ItemStatus
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ItemRepository(BaseRepository[Item]):
    """
    Async repository for Item model with custom query methods.

    Extends BaseRepository to provide Item-specific database operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize ItemRepository with async session.

        Parameters
        ----------
        session : AsyncSession
            Async database session (injected via FastAPI Depends)
        """
        super().__init__(Item, session)

    # MARK: Read
    async def get_by_public_id(self, public_id: str) -> Item | None:
        """
        Get item by public ID (UUID).

        Parameters
        ----------
        public_id : str
            Public UUID identifier

        Returns
        -------
        Item | None
            Item instance if found, None otherwise
        """
        try:
            stmt = select(Item).where(
                Item.public_id == public_id,
                Item.is_deleted.is_(False),
            )
            result = await self.session.execute(stmt)
            item = result.scalar_one_or_none()

            if item:
                logger.debug(f"Found item with public ID {public_id}")
            else:
                logger.debug(f"Item with public ID {public_id} not found")

            return item

        except SQLAlchemyError as e:
            logger.error(f"Failed to get item by public ID {public_id}: {e}")
            raise

    async def get_by_status(
        self,
        status: ItemStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Item]:
        """
        Get all items with specific status.

        Parameters
        ----------
        status : ItemStatus
            Item status to filter by
        skip : int, optional
            Number of records to skip (default: 0)
        limit : int, optional
            Maximum records to return (default: 100)

        Returns
        -------
        list[Item]
            List of items with matching status
        """
        try:
            stmt = (
                select(Item)
                .where(Item.status == status, Item.is_deleted.is_(False))
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            items = list(result.scalars().all())

            logger.debug(f"Retrieved {len(items)} items with status {status.value}")
            return items

        except SQLAlchemyError as e:
            logger.error(f"Failed to get items by status {status.value}: {e}")
            raise

    async def get_by_owner(
        self,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Item]:
        """
        Get all items owned by a specific user.

        Parameters
        ----------
        owner_id : int
            User ID of the owner
        skip : int, optional
            Number of records to skip (default: 0)
        limit : int, optional
            Maximum records to return (default: 100)

        Returns
        -------
        list[Item]
            List of items owned by the user
        """
        try:
            stmt = (
                select(Item)
                .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
                .order_by(Item.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            items = list(result.scalars().all())

            logger.debug(f"Retrieved {len(items)} items for owner {owner_id}")
            return items

        except SQLAlchemyError as e:
            logger.error(f"Failed to get items for owner {owner_id}: {e}")
            raise

    async def search_by_name(self, query: str, limit: int = 50) -> list[Item]:
        """
        Search items by name (case-insensitive partial match).

        Parameters
        ----------
        query : str
            Search query for item name
        limit : int, optional
            Maximum records to return (default: 50)

        Returns
        -------
        list[Item]
            List of items matching search query
        """
        try:
            stmt = (
                select(Item)
                .where(Item.name.ilike(f"%{query}%"), Item.is_deleted.is_(False))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            items = list(result.scalars().all())

            logger.debug(f"Found {len(items)} items matching query '{query}'")
            return items

        except SQLAlchemyError as e:
            logger.error(f"Failed to search items by name '{query}': {e}")
            raise

    # MARK: Paginated Queries
    async def get_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        status: ItemStatus | None = None,
    ) -> tuple[list[Item], int]:
        """
        Get items with database-level pagination.

        Parameters
        ----------
        skip : int, optional
            Number of records to skip (default: 0)
        limit : int, optional
            Maximum records to return (default: 20)
        status : ItemStatus | None, optional
            Filter by status if provided

        Returns
        -------
        tuple[list[Item], int]
            Tuple of (items list, total count)
        """
        try:
            # Base query with soft delete filter
            base_query = select(Item).where(Item.is_deleted.is_(False))
            count_query = select(func.count()).select_from(Item).where(Item.is_deleted.is_(False))

            # Add status filter if provided
            if status:
                base_query = base_query.where(Item.status == status)
                count_query = count_query.where(Item.status == status)

            # Get total count
            total = await self.session.execute(count_query)
            total_count = total.scalar() or 0

            # Get paginated results
            stmt = base_query.order_by(Item.created_at.desc()).offset(skip).limit(limit)
            result = await self.session.execute(stmt)
            items = list(result.scalars().all())

            logger.debug(
                f"Retrieved {len(items)} of {total_count} items (skip={skip}, limit={limit})"
            )
            return items, total_count

        except SQLAlchemyError as e:
            logger.error(f"Failed to get paginated items: {e}")
            raise

    # MARK: Create
    async def create_item(
        self,
        name: str,
        owner_id: int,
        description: str | None = None,
        status: ItemStatus = ItemStatus.DRAFT,
    ) -> Item:
        """
        Create a new item.

        Parameters
        ----------
        name : str
            Item name
        owner_id : int
            User ID of the owner
        description : str | None, optional
            Item description
        status : ItemStatus, optional
            Initial status (default: DRAFT)

        Returns
        -------
        Item
            Created item instance
        """
        try:
            item = Item(
                name=name,
                description=description,
                status=status,
                owner_id=owner_id,
            )
            self.session.add(item)
            await self.flush()
            await self.session.refresh(item)

            logger.info(f"Created item '{name}' (ID: {item.id}) for owner {owner_id}")
            return item

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to create item: {e}")
            raise
