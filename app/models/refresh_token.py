"""
RefreshToken model for JWT refresh token storage.

This module defines the RefreshToken model which stores refresh tokens
with support for token rotation and family tracking.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base):
    """
    RefreshToken model for secure token storage.

    Implements token rotation with family tracking to detect
    refresh token reuse attacks. When a token is reused after
    being rotated, the entire token family is revoked.

    Attributes
    ----------
    id : int
        Primary key
    user_id : int
        Foreign key to user
    token_hash : str
        SHA-256 hash of the refresh token (never store raw tokens)
    token_family : str
        UUID identifying the token family for rotation
    expires_at : datetime
        When the token expires
    is_revoked : bool
        Whether the token has been revoked
    revoked_at : datetime | None
        When the token was revoked
    user : User
        Relationship to the user
    """

    __tablename__ = "refresh_tokens"

    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this refresh token",
    )

    # Token data (never store raw tokens!)
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hash of the refresh token",
    )

    # Token family for rotation tracking
    token_family: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="UUID identifying the token family for rotation",
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When this token expires",
    )

    # Revocation
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        comment="Whether this token has been revoked",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this token was revoked",
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_expired(self) -> bool:
        """
        Check if token is expired.

        Returns
        -------
        bool
            True if token is expired
        """
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """
        Check if token is valid (not expired and not revoked).

        Returns
        -------
        bool
            True if token is valid
        """
        return not self.is_expired and not self.is_revoked

    def revoke(self) -> None:
        """Mark this token as revoked."""
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """
        String representation of RefreshToken.

        Returns
        -------
        str
            Token representation (safe, no sensitive data)
        """
        return f"<RefreshToken user_id={self.user_id} family={self.token_family[:8]}...>"
