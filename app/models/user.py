"""
User model for authentication and user management.

This module defines the User model with support for:
- Email-based authentication
- Role-based access control
- Password hashing with Argon2
- Soft delete and timestamps
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken


class UserRole(str, PyEnum):
    """
    User roles for access control.

    Using (str, PyEnum) makes the enum JSON-serializable
    and allows string comparison.
    """

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(Base, TimestampMixin, PublicIdMixin):
    """
    User model for authentication and authorization.

    Attributes
    ----------
    id : int
        Internal primary key (never expose in API)
    public_id : str
        Public UUID for API endpoints
    email : str
        User's email address (unique)
    hashed_password : str
        Argon2 hashed password
    first_name : str
        User's first name
    last_name : str
        User's last name
    role : UserRole
        User's role for access control
    is_active : bool
        Whether the account is active
    last_login_at : datetime | None
        Last successful login timestamp
    refresh_tokens : list[RefreshToken]
        User's refresh tokens
    """

    __tablename__ = "users"

    # Email (unique identifier for login)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User's email address for authentication",
    )

    # Password (never store plain text!)
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Argon2 hashed password",
    )

    # Profile information
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's first name",
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's last name",
    )

    # Role for access control
    role: Mapped[UserRole] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        comment="User's role for access control",
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
        comment="Whether the account is active",
    )

    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        """
        Get user's full name.

        Returns
        -------
        str
            Full name (first + last)
        """
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        """
        Check if user has admin privileges.

        Returns
        -------
        bool
            True if admin or super_admin
        """
        return self.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        """
        Check if user is a super admin.

        Returns
        -------
        bool
            True if super_admin
        """
        return self.role == UserRole.SUPER_ADMIN

    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password.

        Parameters
        ----------
        password : str
            Plain text password to hash
        """
        from app.core.security.password import password_service

        self.hashed_password = password_service.hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.

        Parameters
        ----------
        password : str
            Plain text password to verify

        Returns
        -------
        bool
            True if password matches
        """
        from app.core.security.password import password_service

        return password_service.verify(password, self.hashed_password)

    def update_last_login(self) -> None:
        """Update the last login timestamp to now."""
        self.last_login_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """
        String representation of User.

        Returns
        -------
        str
            User representation (safe, no sensitive data)
        """
        return f"<User {self.email} (role={self.role.value})>"
