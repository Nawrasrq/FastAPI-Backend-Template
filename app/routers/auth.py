"""
Authentication router for user registration, login, and token management.

This module provides FastAPI routes for authentication operations.
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUserId
from app.core.responses import success_response
from app.db.session import get_db
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schemas import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user_schemas import UserRegister

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# MARK: Dependencies
async def get_auth_service(db: AsyncSession = Depends(get_db)):
    """
    Dependency to create AuthService with injected repositories.

    This is the FastAPI pattern for dependency injection.
    """
    from app.services.auth_service import AuthService

    return AuthService(
        user_repo=UserRepository(db),
        token_repo=RefreshTokenRepository(db),
    )


# MARK: Routes
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    summary="Register new user",
    description="Create a new user account and return authentication tokens.",
)
async def register(
    data: UserRegister,
    service=Depends(get_auth_service),
):
    """
    Register a new user.

    Creates a new user account with the provided email and password,
    then returns JWT access and refresh tokens.

    Parameters
    ----------
    data : UserRegister
        Registration data (email, password, first_name, last_name)

    Returns
    -------
    dict
        Success response with token data
    """
    token_response: TokenResponse = await service.register(data)
    logger.info(f"User registered: {data.email}")
    return success_response(token_response.model_dump())


@router.post(
    "/login",
    response_model=None,
    summary="User login",
    description="Authenticate user with email and password.",
)
async def login(
    data: LoginRequest,
    service=Depends(get_auth_service),
):
    """
    Authenticate user and return tokens.

    Parameters
    ----------
    data : LoginRequest
        Login credentials (email, password)

    Returns
    -------
    dict
        Success response with token data
    """
    token_response: TokenResponse = await service.login(data)
    logger.info(f"User logged in: {data.email}")
    return success_response(token_response.model_dump())


@router.post(
    "/refresh",
    response_model=None,
    summary="Refresh tokens",
    description="Exchange refresh token for new access and refresh tokens.",
)
async def refresh_tokens(
    data: RefreshRequest,
    service=Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.

    Implements token rotation - the old refresh token is invalidated
    and a new token pair is returned.

    Parameters
    ----------
    data : RefreshRequest
        Refresh token

    Returns
    -------
    dict
        Success response with new token data
    """
    token_response: TokenResponse = await service.refresh_tokens(data.refresh_token)
    return success_response(token_response.model_dump())


@router.post(
    "/logout",
    response_model=None,
    summary="Logout",
    description="Revoke refresh token to logout from current device.",
)
async def logout(
    data: RefreshRequest,
    service=Depends(get_auth_service),
):
    """
    Logout user by revoking refresh token.

    Parameters
    ----------
    data : RefreshRequest
        Refresh token to revoke

    Returns
    -------
    dict
        Success response
    """
    await service.logout(data.refresh_token)
    return success_response({"message": "Logged out successfully"})


@router.post(
    "/logout-all",
    response_model=None,
    summary="Logout from all devices",
    description="Revoke all refresh tokens for the current user.",
)
async def logout_all(
    user_id: CurrentUserId,
    service=Depends(get_auth_service),
):
    """
    Logout user from all devices.

    Requires authentication. Revokes all refresh tokens
    associated with the current user.

    Parameters
    ----------
    user_id : int
        Current user's ID (injected via dependency)

    Returns
    -------
    dict
        Success response with count of revoked tokens
    """
    count = await service.logout_all(user_id)
    return success_response(
        {
            "message": "Logged out from all devices",
            "tokens_revoked": count,
        }
    )
