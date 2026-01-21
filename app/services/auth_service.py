"""
Authentication service for user registration, login, and token management.

This module provides the async service layer for authentication operations,
implementing secure JWT-based authentication with refresh token rotation.
"""

import logging

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security.jwt import token_service
from app.core.security.password import password_service
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schemas import LoginRequest, TokenResponse
from app.schemas.user_schemas import UserRegister

logger = logging.getLogger(__name__)


class AuthService:
    """
    Async authentication business logic with refresh token rotation.

    Implements secure authentication patterns:
    - JWT access tokens (short-lived)
    - Refresh token rotation with family tracking
    - Token reuse detection (revokes entire family)
    - Argon2id password hashing

    Parameters
    ----------
    user_repo : UserRepository
        User repository instance (injected)
    token_repo : RefreshTokenRepository
        Refresh token repository instance (injected)
    """

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ):
        """
        Initialize AuthService with repositories.

        Parameters
        ----------
        user_repo : UserRepository
            Repository for user operations
        token_repo : RefreshTokenRepository
            Repository for refresh token operations
        """
        self.user_repo = user_repo
        self.token_repo = token_repo

    # MARK: Authentication
    async def register(self, data: UserRegister) -> TokenResponse:
        """
        Register a new user and return authentication tokens.

        Parameters
        ----------
        data : UserRegister
            Registration data with email, password, first_name, last_name

        Returns
        -------
        TokenResponse
            Access token, refresh token, and metadata

        Raises
        ------
        ConflictError
            If email already exists (raised by repository)
        ValidationError
            If password doesn't meet strength requirements (validated by schema)
        """
        # Create user (repository handles duplicate check and password hashing)
        user = await self.user_repo.create_user(
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
        )

        # Generate tokens and store refresh token
        token_response = await self._create_token_response(user)

        # Commit transaction
        await self.user_repo.commit()

        logger.info(f"User registered: {user.email} (ID: {user.id})")
        return token_response

    async def login(self, data: LoginRequest) -> TokenResponse:
        """
        Authenticate user and return tokens.

        Parameters
        ----------
        data : LoginRequest
            Login credentials (email and password)

        Returns
        -------
        TokenResponse
            Access token, refresh token, and metadata

        Raises
        ------
        UnauthorizedError
            If credentials are invalid or user is inactive/deleted
        """
        # Find user by email
        user = await self.user_repo.find_by_email(data.email)

        if not user:
            logger.warning(f"Login attempt for non-existent email: {data.email}")
            raise UnauthorizedError(message="Invalid email or password")

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {data.email}")
            raise UnauthorizedError(message="Account is deactivated")

        # Check if user is deleted
        if user.is_deleted:
            logger.warning(f"Login attempt for deleted user: {data.email}")
            raise UnauthorizedError(message="Invalid email or password")

        # Verify password
        if not user.check_password(data.password):
            logger.warning(f"Invalid password for user: {data.email}")
            raise UnauthorizedError(message="Invalid email or password")

        # Check if password needs rehash (security upgrade)
        if password_service.needs_rehash(user.hashed_password):
            logger.info(f"Rehashing password for user: {user.id}")
            user.set_password(data.password)
            await self.user_repo.flush()

        # Update last login
        user.update_last_login()

        # Generate tokens (new family for new login session)
        token_response = await self._create_token_response(user)

        # Commit transaction
        await self.user_repo.commit()

        logger.info(f"User logged in: {user.email}")
        return token_response

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Rotate refresh token and return new token pair.

        Implements secure token rotation with family tracking.
        If a revoked token is used (potential theft), revokes entire family.

        Parameters
        ----------
        refresh_token : str
            Current refresh token

        Returns
        -------
        TokenResponse
            New access token, refresh token, and metadata

        Raises
        ------
        UnauthorizedError
            If token is invalid, expired, or revoked
        """
        # Decode and validate refresh token
        try:
            _ = token_service.decode_token(refresh_token, "refresh")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            raise UnauthorizedError(message="Invalid or expired refresh token") from None

        # Hash token and look up in database
        token_hash = token_service.hash_token(refresh_token)
        stored_token = await self.token_repo.find_by_token_hash(token_hash)

        if not stored_token:
            logger.warning("Refresh token not found in database")
            raise UnauthorizedError(message="Invalid refresh token")

        # Check if token is revoked (potential token theft!)
        if stored_token.is_revoked:
            # Security: Revoke entire token family
            logger.warning(
                f"Revoked token reuse detected! Revoking family: {stored_token.token_family}"
            )
            await self.token_repo.revoke_family(stored_token.token_family)
            await self.token_repo.commit()
            raise UnauthorizedError(
                message="Session invalidated for security. Please log in again."
            )

        # Get user
        user = await self.user_repo.get_by_id(stored_token.user_id)
        if not user or not user.is_active or user.is_deleted:
            logger.warning(f"Token refresh for invalid user: {stored_token.user_id}")
            raise UnauthorizedError(message="User account is not available")

        # Revoke current token
        await self.token_repo.revoke_token(token_hash)

        # Generate new tokens with same token_family (rotation)
        token_response = await self._create_token_response(
            user, token_family=stored_token.token_family
        )

        # Commit transaction
        await self.token_repo.commit()

        logger.info(f"Tokens refreshed for user: {user.id}")
        return token_response

    async def logout(self, refresh_token: str) -> None:
        """
        Revoke refresh token (logout from current device).

        Parameters
        ----------
        refresh_token : str
            Refresh token to revoke
        """
        # Validate token format
        try:
            token_service.decode_token(refresh_token, "refresh")
        except jwt.InvalidTokenError:
            # Don't reveal if token was valid - just succeed silently
            logger.debug("Logout with invalid token - ignoring")
            return

        # Hash and revoke
        token_hash = token_service.hash_token(refresh_token)
        await self.token_repo.revoke_token(token_hash)
        await self.token_repo.commit()

        logger.info("User logged out (token revoked)")

    async def logout_all(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for a user (logout from all devices).

        Parameters
        ----------
        user_id : int
            User ID whose tokens to revoke

        Returns
        -------
        int
            Number of tokens revoked
        """
        count = await self.token_repo.revoke_user_tokens(user_id)
        await self.token_repo.commit()

        logger.info(f"Logged out user {user_id} from all devices ({count} tokens)")
        return count

    # MARK: Private Helpers
    async def _create_token_response(
        self, user: User, token_family: str | None = None
    ) -> TokenResponse:
        """
        Generate tokens and store refresh token in database.

        Parameters
        ----------
        user : User
            User to generate tokens for
        token_family : str | None
            Token family for rotation (None creates new family)

        Returns
        -------
        TokenResponse
            Token response schema with access and refresh tokens
        """
        # Create access token
        access_token, _ = token_service.create_access_token(
            user_id=user.id,
            email=user.email,
            permissions=[],  # Add permissions based on role if needed
            role=user.role.value if user.role else None,
            is_super_admin=user.is_super_admin,
        )

        # Create refresh token
        refresh_token, token_hash, token_family, refresh_expires = (
            token_service.create_refresh_token(
                user_id=user.id,
                email=user.email,
                token_family=token_family,
            )
        )

        # Store refresh token hash in database
        await self.token_repo.create_token(
            user_id=user.id,
            token_hash=token_hash,
            token_family=token_family,
            expires_at=refresh_expires,
        )

        # Calculate expires_in (seconds until access token expires)
        expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in,
        )
