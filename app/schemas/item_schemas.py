"""
Pydantic schemas for Item model.

This module defines request and response schemas for Item CRUD operations.
"""

from pydantic import Field

from app.models.item import ItemStatus
from app.schemas.base import BaseResponseSchema, BaseSchema


class ItemCreate(BaseSchema):
    """
    Schema for creating a new item.

    Attributes
    ----------
    name : str
        Item name (max 200 characters)
    description : str | None
        Optional item description
    status : ItemStatus
        Item status (default: DRAFT)
    """

    name: str = Field(min_length=1, max_length=200, description="Item name (required)")
    description: str | None = Field(default=None, description="Item description")
    status: ItemStatus = Field(default=ItemStatus.DRAFT, description="Item status")


class ItemUpdate(BaseSchema):
    """
    Schema for updating an existing item.

    All fields are optional - only provided fields will be updated.

    Attributes
    ----------
    name : str | None
        Item name (max 200 characters)
    description : str | None
        Item description
    status : ItemStatus | None
        Item status
    """

    name: str | None = Field(default=None, min_length=1, max_length=200, description="Item name")
    description: str | None = Field(default=None, description="Item description")
    status: ItemStatus | None = Field(default=None, description="Item status")


class ItemResponse(BaseResponseSchema):
    """
    Schema for item response with all fields.

    Attributes
    ----------
    name : str
        Item name
    description : str | None
        Item description
    status : str
        Item status
    owner_id : str
        Public ID of the owner (for reference)
    """

    name: str = Field(description="Item name")
    description: str | None = Field(description="Item description")
    status: str = Field(description="Item status")
