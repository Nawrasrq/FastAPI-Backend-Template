"""
User service for user management operations.

This module provides the async service layer for user-related operations.
"""

import logging

from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security.password import password_service
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """
    Async user management service.

    Provides business logic for user operations including
    profile updates, password changes, and account management.

    Parameters
    ----------
    user_repo : UserRepository
        User repository instance (injected)
    """

    def __init__(self, user_repo: UserRepository):
        """
        Initialize UserService with repository.

        Parameters
        ----------
        user_repo : UserRepository
            Repository for user operations
        """
        self.user_repo = user_repo

    # MARK: Read
    async def get_by_id(self, user_id: int) -> User:
        """
        Get user by internal ID.

        Parameters
        ----------
        user_id : int
            Internal user ID

        Returns
        -------
        User
            User instance

        Raises
        ------
        NotFoundError
            If user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.is_deleted:
            raise NotFoundError(message="User not found", resource="User")
        return user

    async def get_by_public_id(self, public_id: str) -> User:
        """
        Get user by public ID (UUID).

        Parameters
        ----------
        public_id : str
            Public UUID identifier

        Returns
        -------
        User
            User instance

        Raises
        ------
        NotFoundError
            If user not found
        """
        user = await self.user_repo.get_by_public_id(public_id)
        if not user:
            raise NotFoundError(message="User not found", resource="User")
        return user

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get list of active users with pagination.

        Parameters
        ----------
        skip : int, optional
            Number of records to skip
        limit : int, optional
            Maximum records to return

        Returns
        -------
        list[User]
            List of active users
        """
        return await self.user_repo.get_active_users(skip=skip, limit=limit)

    # MARK: Update
    async def update_profile(self, user_id: int, data: UserUpdate) -> User:
        """
        Update user profile information.

        Parameters
        ----------
        user_id : int
            User ID to update
        data : UserUpdate
            Update data (only provided fields will be updated)

        Returns
        -------
        User
            Updated user instance

        Raises
        ------
        NotFoundError
            If user not found
        """
        user = await self.get_by_id(user_id)

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)

        await self.user_repo.flush()
        await self.user_repo.commit()

        logger.info(f"Updated profile for user {user_id}")
        return user

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user's password.

        Parameters
        ----------
        user_id : int
            User ID
        old_password : str
            Current password for verification
        new_password : str
            New password to set

        Returns
        -------
        bool
            True if password changed successfully

        Raises
        ------
        NotFoundError
            If user not found
        UnauthorizedError
            If old password is incorrect
        """
        user = await self.get_by_id(user_id)

        # Verify old password
        if not user.check_password(old_password):
            logger.warning(f"Invalid old password for user {user_id}")
            raise UnauthorizedError(message="Current password is incorrect")

        # Validate new password strength
        is_valid, violations = password_service.validate_strength(new_password)
        if not is_valid:
            from app.core.exceptions import ValidationError

            raise ValidationError(
                message="Password does not meet requirements",
                payload={"violations": violations},
            )

        # Update password
        user.set_password(new_password)
        await self.user_repo.flush()
        await self.user_repo.commit()

        logger.info(f"Password changed for user {user_id}")
        return True

    # MARK: Account Management
    async def deactivate_account(self, user_id: int) -> bool:
        """
        Deactivate a user account.

        Parameters
        ----------
        user_id : int
            User ID to deactivate

        Returns
        -------
        bool
            True if deactivated

        Raises
        ------
        NotFoundError
            If user not found
        """
        user = await self.get_by_id(user_id)
        user.is_active = False

        await self.user_repo.flush()
        await self.user_repo.commit()

        logger.info(f"Deactivated user {user_id}")
        return True

    async def delete_account(self, user_id: int) -> bool:
        """
        Soft delete a user account.

        Parameters
        ----------
        user_id : int
            User ID to delete

        Returns
        -------
        bool
            True if deleted

        Raises
        ------
        NotFoundError
            If user not found
        """
        user = await self.get_by_id(user_id)
        user.soft_delete()

        await self.user_repo.flush()
        await self.user_repo.commit()

        logger.info(f"Soft deleted user {user_id}")
        return True
