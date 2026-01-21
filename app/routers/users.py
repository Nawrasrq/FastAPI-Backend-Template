"""
User router for user management operations.

This module provides FastAPI routes for user profile and account management.
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, CurrentUserId
from app.core.responses import success_response
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schemas import PasswordChangeRequest
from app.schemas.user_schemas import UserResponse, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# MARK: Dependencies
async def get_user_service(db: AsyncSession = Depends(get_db)):
    """Dependency to create UserService with injected repository."""
    from app.services.user_service import UserService

    return UserService(user_repo=UserRepository(db))


# MARK: Routes
@router.get(
    "/me",
    response_model=None,
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user.",
)
async def get_current_user_profile(
    current_user: CurrentUser,
    user_id: CurrentUserId,
    service=Depends(get_user_service),
):
    """
    Get current user's profile.

    Requires authentication. Returns the profile of the user
    associated with the provided access token.

    Returns
    -------
    dict
        Success response with user data
    """
    user = await service.get_by_id(user_id)
    return success_response(UserResponse.model_validate(user).model_dump())


@router.patch(
    "/me",
    response_model=None,
    summary="Update current user profile",
    description="Update the profile of the currently authenticated user.",
)
async def update_current_user_profile(
    data: UserUpdate,
    user_id: CurrentUserId,
    service=Depends(get_user_service),
):
    """
    Update current user's profile.

    Requires authentication. Only provided fields will be updated.

    Parameters
    ----------
    data : UserUpdate
        Profile update data (first_name, last_name)

    Returns
    -------
    dict
        Success response with updated user data
    """
    user = await service.update_profile(user_id, data)
    logger.info(f"Profile updated for user {user_id}")
    return success_response(UserResponse.model_validate(user).model_dump())


@router.post(
    "/me/change-password",
    response_model=None,
    summary="Change password",
    description="Change the password for the currently authenticated user.",
)
async def change_password(
    data: PasswordChangeRequest,
    user_id: CurrentUserId,
    service=Depends(get_user_service),
):
    """
    Change current user's password.

    Requires authentication and verification of the old password.

    Parameters
    ----------
    data : PasswordChangeRequest
        Old and new passwords

    Returns
    -------
    dict
        Success response
    """
    await service.change_password(user_id, data.old_password, data.new_password)
    logger.info(f"Password changed for user {user_id}")
    return success_response({"message": "Password changed successfully"})


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Delete current user account",
    description="Soft delete the currently authenticated user's account.",
)
async def delete_current_user_account(
    user_id: CurrentUserId,
    service=Depends(get_user_service),
):
    """
    Delete current user's account.

    Requires authentication. Performs a soft delete.

    Returns
    -------
    dict
        Success response
    """
    await service.delete_account(user_id)
    logger.info(f"Account deleted for user {user_id}")
    return success_response({"message": "Account deleted successfully"})


@router.get(
    "/{public_id}",
    response_model=None,
    summary="Get user by public ID",
    description="Get a user's public profile by their public ID.",
)
async def get_user_by_public_id(
    public_id: str,
    service=Depends(get_user_service),
):
    """
    Get user by public ID.

    Parameters
    ----------
    public_id : str
        User's public UUID

    Returns
    -------
    dict
        Success response with user data
    """
    user = await service.get_by_public_id(public_id)
    return success_response(UserResponse.model_validate(user).model_dump())
