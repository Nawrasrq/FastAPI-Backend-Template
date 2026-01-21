"""
Base model and mixins for common database functionality.

Provides reusable components for models following DRY principles.
Uses SQLAlchemy 2.0 with async support.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PublicIdMixin:
    """
    Mixin for adding a public UUID identifier.

    Adds a public_id field that should be used for API endpoints instead of
    exposing the internal integer primary key. This enhances security by:
    - Preventing enumeration attacks
    - Hiding database sequence information
    - Providing URL-safe identifiers
    """

    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
        comment="Public UUID identifier for API endpoints",
    )


class TimestampMixin:
    """
    Mixin for automatic timestamp tracking.

    Adds created_at and updated_at fields to any model with timezone awareness.
    Uses database-level defaults (func.now()) for consistency across all clients.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the record was last updated",
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Adds deleted_at and is_deleted fields to any model.
    Instead of deleting records, they are marked as deleted.
    Useful for audit trails and data recovery.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp when the record was soft deleted (null = not deleted)",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
        default=False,
        server_default="false",
        comment="Whether the record is soft deleted",
    )

    def soft_delete(self) -> None:
        """Mark this record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class Base(DeclarativeBase, SoftDeleteMixin):
    """
    Base model with common fields.

    All models should inherit from this class to get:
    - Auto-incrementing integer primary key
    - Soft delete functionality (is_deleted, deleted_at)

    Usage
    -----
    ```python
    class User(Base, TimestampMixin, PublicIdMixin):
        __tablename__ = "users"
        email: Mapped[str] = mapped_column(String(255), unique=True)
    ```
    """

    __abstract__ = True  # Don't create table for this class

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    def __repr__(self) -> str:
        """
        String representation of the model.

        Returns
        -------
        str
            Model representation
        """
        return f"<{self.__class__.__name__}(id={self.id})>"
