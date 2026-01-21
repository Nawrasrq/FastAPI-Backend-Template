"""
RefreshToken repository for JWT token management.

This module provides async data access methods for refresh token operations
including token rotation, revocation, and cleanup.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """
    Async repository for RefreshToken model with token management methods.

    Extends BaseRepository to provide token-specific operations including
    lookup by token hash, family revocation, and expired token cleanup.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize RefreshTokenRepository with async session.

        Parameters
        ----------
        session : AsyncSession
            Async database session (injected via FastAPI Depends)
        """
        super().__init__(RefreshToken, session)

    # MARK: Read
    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Find refresh token by token hash.

        Parameters
        ----------
        token_hash : str
            SHA256 hash of the refresh token

        Returns
        -------
        RefreshToken | None
            RefreshToken instance if found, None otherwise
        """
        try:
            stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            result = await self.session.execute(stmt)
            token = result.scalar_one_or_none()

            if token:
                logger.debug(f"Found refresh token with hash {token_hash[:16]}...")
            else:
                logger.debug(f"Refresh token with hash {token_hash[:16]}... not found")

            return token

        except SQLAlchemyError as e:
            logger.error(f"Failed to find refresh token by hash: {e}")
            raise

    async def get_user_tokens(self, user_id: int) -> list[RefreshToken]:
        """
        Get all active (non-revoked, non-expired) tokens for a user.

        Parameters
        ----------
        user_id : int
            User ID

        Returns
        -------
        list[RefreshToken]
            List of active refresh tokens
        """
        try:
            now = datetime.now(timezone.utc)

            stmt = select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > now,
            )
            result = await self.session.execute(stmt)
            tokens = list(result.scalars().all())

            logger.debug(f"Retrieved {len(tokens)} active tokens for user {user_id}")
            return tokens

        except SQLAlchemyError as e:
            logger.error(f"Failed to get tokens for user {user_id}: {e}")
            raise

    # MARK: Create
    async def create_token(
        self,
        user_id: int,
        token_hash: str,
        token_family: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """
        Create a new refresh token.

        Parameters
        ----------
        user_id : int
            User ID who owns the token
        token_hash : str
            SHA256 hash of the refresh token
        token_family : str
            Family ID for token rotation tracking
        expires_at : datetime
            Token expiration timestamp

        Returns
        -------
        RefreshToken
            Created refresh token instance
        """
        try:
            token = RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                token_family=token_family,
                expires_at=expires_at,
            )
            self.session.add(token)
            await self.flush()
            await self.session.refresh(token)

            logger.info(f"Created refresh token for user {user_id} (family: {token_family})")
            return token

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to create refresh token: {e}")
            raise

    # MARK: Revocation
    async def revoke_token(self, token_hash: str) -> bool:
        """
        Revoke a specific refresh token.

        Parameters
        ----------
        token_hash : str
            SHA256 hash of the token to revoke

        Returns
        -------
        bool
            True if revoked, False if token not found
        """
        try:
            token = await self.find_by_token_hash(token_hash)
            if not token:
                logger.warning(f"Token not found for revocation: {token_hash[:16]}...")
                return False

            token.revoke()
            await self.flush()

            logger.info(f"Revoked refresh token {token.id} (family: {token.token_family})")
            return True

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to revoke token: {e}")
            raise

    async def revoke_family(self, token_family: str) -> int:
        """
        Revoke all tokens in a token family.

        This is used for security when token reuse is detected, invalidating
        all tokens in the rotation family.

        Parameters
        ----------
        token_family : str
            Family ID of tokens to revoke

        Returns
        -------
        int
            Number of tokens revoked
        """
        try:
            stmt = select(RefreshToken).where(
                RefreshToken.token_family == token_family,
                RefreshToken.is_revoked.is_(False),
            )
            result = await self.session.execute(stmt)
            tokens = result.scalars().all()

            count = 0
            for token in tokens:
                token.revoke()
                count += 1

            await self.flush()

            logger.warning(
                f"Revoked {count} tokens in family {token_family} (potential security breach)"
            )
            return count

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to revoke token family {token_family}: {e}")
            raise

    async def revoke_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a specific user.

        Used when user logs out from all devices or account is compromised.

        Parameters
        ----------
        user_id : int
            User ID whose tokens to revoke

        Returns
        -------
        int
            Number of tokens revoked
        """
        try:
            stmt = select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            result = await self.session.execute(stmt)
            tokens = result.scalars().all()

            count = 0
            for token in tokens:
                token.revoke()
                count += 1

            await self.flush()

            logger.info(f"Revoked {count} tokens for user {user_id}")
            return count

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to revoke tokens for user {user_id}: {e}")
            raise

    # MARK: Cleanup
    async def cleanup_expired(self) -> int:
        """
        Delete expired refresh tokens.

        This should be run periodically to clean up the database.

        Returns
        -------
        int
            Number of expired tokens deleted
        """
        try:
            now = datetime.now(timezone.utc)

            stmt = delete(RefreshToken).where(RefreshToken.expires_at < now)
            result = await self.session.execute(stmt)
            await self.commit()

            count = result.rowcount
            logger.info(f"Cleaned up {count} expired refresh tokens")
            return count

        except SQLAlchemyError as e:
            await self.rollback()
            logger.error(f"Failed to cleanup expired tokens: {e}")
            raise
