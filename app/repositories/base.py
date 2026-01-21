"""
Base repository with generic async CRUD operations.

This module provides a generic repository pattern implementation with
type safety using Python generics and async SQLAlchemy 2.0.
"""

import logging
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

# Type variable bound to SQLAlchemy DeclarativeBase
ModelType = TypeVar("ModelType", bound=Base)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType]):
    """
    Generic async repository with type-safe CRUD operations.

    This repository provides common database operations for any SQLAlchemy model,
    with full type safety through Python generics and async support.

    Parameters
    ----------
    model : type[ModelType]
        The SQLAlchemy model class this repository manages
    session : AsyncSession
        Async database session (injected via FastAPI Depends)

    Example
    -------
    ```python
    class UserRepository(BaseRepository[User]):
        def __init__(self, session: AsyncSession):
            super().__init__(User, session)

        async def find_by_email(self, email: str) -> User | None:
            stmt = select(User).where(User.email == email)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
    ```
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """
        Initialize repository with model class and async session.

        Parameters
        ----------
        model : type[ModelType]
            SQLAlchemy model class
        session : AsyncSession
            Async database session
        """
        self.model = model
        self.session = session

    # MARK: Transaction Control
    async def rollback(self) -> None:
        """
        Rollback current transaction.

        Raises
        ------
        SQLAlchemyError
            If database operation fails
        """
        try:
            await self.session.rollback()
            logger.debug("Transaction rolled back")
        except SQLAlchemyError as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise

    async def flush(self) -> None:
        """
        Flush pending changes without committing.

        This stages changes and generates IDs but doesn't
        make them permanent. Use in repositories to allow
        services to control transaction boundaries.

        Raises
        ------
        SQLAlchemyError
            If flush fails
        """
        try:
            await self.session.flush()
            logger.debug("Session flushed")
        except SQLAlchemyError as e:
            logger.error(f"Failed to flush session: {e}")
            raise

    async def commit(self) -> None:
        """
        Commit current transaction.

        Should typically be called by services, not repositories,
        to maintain proper transaction boundaries.

        Raises
        ------
        SQLAlchemyError
            If commit fails
        """
        try:
            await self.session.commit()
            logger.debug("Transaction committed")
        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to commit transaction: {e}")
            raise

    # MARK: Count & Exists
    async def count(self, **filters) -> int:
        """
        Count records matching filters.

        Parameters
        ----------
        **filters
            Field filters (e.g., status="active")

        Returns
        -------
        int
            Number of matching records
        """
        try:
            stmt = select(func.count()).select_from(self.model)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)

            result = await self.session.execute(stmt)
            count_value = result.scalar() or 0

            logger.debug(f"Counted {count_value} {self.model.__name__} records matching filters")
            return count_value

        except SQLAlchemyError as e:
            logger.error(f"Failed to count {self.model.__name__}: {e}")
            raise

    async def exists(self, **filters) -> bool:
        """
        Check if record exists matching filters.

        Parameters
        ----------
        **filters
            Field filters (e.g., email="test@example.com")

        Returns
        -------
        bool
            True if record exists
        """
        return await self.count(**filters) > 0

    # MARK: Read
    async def get_by_id(self, id: int) -> ModelType | None:
        """
        Get record by ID.

        Parameters
        ----------
        id : int
            Record ID (primary key)

        Returns
        -------
        ModelType | None
            Model instance if found, None otherwise

        Raises
        ------
        SQLAlchemyError
            If database operation fails
        """
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = await self.session.execute(stmt)
            instance = result.scalar_one_or_none()

            if instance:
                logger.debug(f"Found {self.model.__name__} with ID {id}")
            else:
                logger.debug(f"{self.model.__name__} with ID {id} not found")

            return instance

        except SQLAlchemyError as e:
            logger.error(f"Failed to get {self.model.__name__} by ID {id}: {e}")
            raise

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        """
        Get all records with pagination.

        Parameters
        ----------
        skip : int, optional
            Number of records to skip (default: 0)
        limit : int, optional
            Maximum number of records to return (default: 100)
        include_deleted : bool, optional
            Include soft-deleted records (default: False)

        Returns
        -------
        list[ModelType]
            List of model instances

        Raises
        ------
        SQLAlchemyError
            If database operation fails
        """
        try:
            stmt = select(self.model)

            # Exclude soft-deleted by default
            if not include_deleted and hasattr(self.model, "is_deleted"):
                stmt = stmt.where(self.model.is_deleted.is_(False))

            stmt = stmt.offset(skip).limit(limit)
            result = await self.session.execute(stmt)
            instances = list(result.scalars().all())

            logger.debug(f"Retrieved {len(instances)} {self.model.__name__} records")
            return instances

        except SQLAlchemyError as e:
            logger.error(f"Failed to get all {self.model.__name__}: {e}")
            raise

    # MARK: Create
    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record.

        Parameters
        ----------
        **kwargs
            Field values for the new record

        Returns
        -------
        ModelType
            Created model instance (with ID populated)

        Raises
        ------
        SQLAlchemyError
            If database operation fails
        """
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            await self.flush()
            await self.session.refresh(instance)

            logger.info(f"Created {self.model.__name__} with ID {instance.id}")
            return instance

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise

    # MARK: Update
    async def update(self, id: int, **kwargs) -> ModelType | None:
        """
        Update record by ID.

        Parameters
        ----------
        id : int
            Record ID
        **kwargs
            Fields to update with new values

        Returns
        -------
        ModelType | None
            Updated model instance if found, None otherwise

        Raises
        ------
        SQLAlchemyError
            If database operation fails
        """
        try:
            instance = await self.get_by_id(id)
            if not instance:
                logger.warning(f"{self.model.__name__} with ID {id} not found for update")
                return None

            # Update fields
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            await self.flush()
            await self.session.refresh(instance)

            logger.info(f"Updated {self.model.__name__} with ID {id}")
            return instance

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to update {self.model.__name__} with ID {id}: {e}")
            raise

    # MARK: Delete
    async def delete(self, id: int) -> bool:
        """
        Permanently delete record by ID.

        Parameters
        ----------
        id : int
            Record ID

        Returns
        -------
        bool
            True if deleted, False if not found

        Raises
        ------
        SQLAlchemyError
            If database operation fails
        """
        try:
            instance = await self.get_by_id(id)
            if not instance:
                logger.warning(f"{self.model.__name__} with ID {id} not found for deletion")
                return False

            await self.session.delete(instance)
            await self.flush()

            logger.info(f"Deleted {self.model.__name__} with ID {id}")
            return True

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to delete {self.model.__name__} with ID {id}: {e}")
            raise

    async def soft_delete(self, id: int) -> bool:
        """
        Soft delete record by ID (set is_deleted=True).

        Only works if model has is_deleted field (inherits from Base).

        Parameters
        ----------
        id : int
            Record ID

        Returns
        -------
        bool
            True if soft deleted, False if not found

        Raises
        ------
        AttributeError
            If model doesn't support soft delete
        SQLAlchemyError
            If database operation fails
        """
        try:
            instance = await self.get_by_id(id)
            if not instance:
                logger.warning(f"{self.model.__name__} with ID {id} not found for soft deletion")
                return False

            if not hasattr(instance, "soft_delete"):
                raise AttributeError(f"{self.model.__name__} does not support soft delete")

            instance.soft_delete()
            await self.flush()

            logger.info(f"Soft deleted {self.model.__name__} with ID {id}")
            return True

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to soft delete {self.model.__name__} with ID {id}: {e}")
            raise
