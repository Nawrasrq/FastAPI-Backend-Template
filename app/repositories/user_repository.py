"""
User repository for async database operations.

This module provides data access methods specific to the User model.
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.user import User
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """
    Async repository for User model with authentication-specific methods.

    Extends BaseRepository to provide User-specific database operations
    including user creation with password hashing and email lookup.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize UserRepository with async session.

        Parameters
        ----------
        session : AsyncSession
            Async database session (injected via FastAPI Depends)
        """
        super().__init__(User, session)

    # MARK: Read
    async def get_by_public_id(self, public_id: str) -> User | None:
        """
        Get user by public ID (UUID).

        Parameters
        ----------
        public_id : str
            Public UUID identifier

        Returns
        -------
        User | None
            User instance if found, None otherwise
        """
        try:
            stmt = select(User).where(
                User.public_id == public_id,
                User.is_deleted.is_(False),
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.debug(f"Found user with public ID {public_id}")
            else:
                logger.debug(f"User with public ID {public_id} not found")

            return user

        except SQLAlchemyError as e:
            logger.error(f"Failed to get user by public ID {public_id}: {e}")
            raise

    async def find_by_email(self, email: str) -> User | None:
        """
        Find user by email address.

        Parameters
        ----------
        email : str
            Email address to search for

        Returns
        -------
        User | None
            User instance if found, None otherwise
        """
        try:
            stmt = select(User).where(
                User.email == email,
                User.is_deleted.is_(False),
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.debug(f"Found user with email {email}")
            else:
                logger.debug(f"User with email {email} not found")

            return user

        except SQLAlchemyError as e:
            logger.error(f"Failed to find user by email {email}: {e}")
            raise

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all active (non-deleted, is_active=True) users.

        Parameters
        ----------
        skip : int, optional
            Number of records to skip (default: 0)
        limit : int, optional
            Maximum records to return (default: 100)

        Returns
        -------
        list[User]
            List of active users
        """
        try:
            stmt = (
                select(User)
                .where(User.is_active, User.is_deleted.is_(False))
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            users = list(result.scalars().all())

            logger.debug(f"Retrieved {len(users)} active users")
            return users

        except SQLAlchemyError as e:
            logger.error(f"Failed to get active users: {e}")
            raise

    # MARK: Create
    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """
        Create a new user with hashed password.

        Parameters
        ----------
        email : str
            User email address (must be unique)
        password : str
            Plain text password (will be hashed)
        first_name : str
            User's first name
        last_name : str
            User's last name

        Returns
        -------
        User
            Created user instance

        Raises
        ------
        ConflictError
            If email already exists
        SQLAlchemyError
            If database operation fails
        """
        try:
            # Check if email already exists (optimistic check)
            if await self.find_by_email(email):
                logger.warning(f"Attempted to create user with duplicate email: {email}")
                raise ConflictError(
                    message=f"User with email {email} already exists", field="email"
                )

            # Create user with hashed password
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                hashed_password="",  # Will be set by set_password
            )
            user.set_password(password)

            self.session.add(user)
            await self.flush()
            await self.session.refresh(user)

            logger.info(f"Created user with email {email} (ID: {user.id})")
            return user

        except IntegrityError as e:
            # Race condition safety: another request created the user
            await self.rollback()
            logger.error(f"Integrity error creating user with email {email}: {e}")
            raise ConflictError(
                message=f"User with email {email} already exists", field="email"
            ) from None
        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to create user with email {email}: {e}")
            raise

    # MARK: Update
    async def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user's password.

        Parameters
        ----------
        user_id : int
            User ID
        new_password : str
            New plain text password (will be hashed)

        Returns
        -------
        bool
            True if password updated, False if user not found
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(f"User with ID {user_id} not found for password update")
                return False

            user.set_password(new_password)
            await self.flush()

            logger.info(f"Updated password for user ID {user_id}")
            return True

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to update password for user ID {user_id}: {e}")
            raise

    async def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate user account.

        Parameters
        ----------
        user_id : int
            User ID

        Returns
        -------
        bool
            True if deactivated, False if user not found
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(f"User with ID {user_id} not found for deactivation")
                return False

            user.is_active = False
            await self.flush()

            logger.info(f"Deactivated user ID {user_id}")
            return True

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to deactivate user ID {user_id}: {e}")
            raise

    async def activate_user(self, user_id: int) -> bool:
        """
        Activate user account.

        Parameters
        ----------
        user_id : int
            User ID

        Returns
        -------
        bool
            True if activated, False if user not found
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(f"User with ID {user_id} not found for activation")
                return False

            user.is_active = True
            await self.flush()

            logger.info(f"Activated user ID {user_id}")
            return True

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to activate user ID {user_id}: {e}")
            raise
