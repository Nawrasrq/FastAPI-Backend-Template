"""
Item model for demonstration of CRUD operations.

This module provides a sample Item model to demonstrate
the MVCS architecture patterns in this template.
"""

from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ItemStatus(str, PyEnum):
    """
    Status values for items.

    Using (str, PyEnum) makes the enum JSON-serializable
    and allows string comparison.
    """

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Item(Base, TimestampMixin, PublicIdMixin):
    """
    Item model demonstrating CRUD patterns.

    Attributes
    ----------
    id : int
        Internal primary key (never expose in API)
    public_id : str
        Public UUID for API endpoints
    name : str
        Item name
    description : str | None
        Optional description
    status : ItemStatus
        Current status
    owner_id : int
        Foreign key to user who owns the item
    owner : User
        Relationship to the owner
    """

    __tablename__ = "items"

    # Item data
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="Item name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional item description",
    )

    # Status
    status: Mapped[ItemStatus] = mapped_column(
        String(20),
        nullable=False,
        default=ItemStatus.DRAFT,
        server_default=ItemStatus.DRAFT.value,
        index=True,
        comment="Current item status",
    )

    # Owner relationship
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this item",
    )
    owner: Mapped["User"] = relationship("User", lazy="selectin")

    def activate(self) -> None:
        """Set item status to active."""
        self.status = ItemStatus.ACTIVE

    def archive(self) -> None:
        """Set item status to archived."""
        self.status = ItemStatus.ARCHIVED

    def __repr__(self) -> str:
        """
        String representation of Item.

        Returns
        -------
        str
            Item representation
        """
        return f"<Item {self.name} (status={self.status.value})>"
