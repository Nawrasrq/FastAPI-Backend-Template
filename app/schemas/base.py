"""
Base Pydantic schema configuration.

This module defines the base schema class with common configuration
for all Pydantic models used in the application.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """
    Base schema with common Pydantic configuration.

    All application schemas should inherit from this class to ensure
    consistent behavior across request/response validation.
    """

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy models
        populate_by_name=True,  # Allow population by field name
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
        validate_assignment=True,  # Validate on field assignment
        use_enum_values=True,  # Use enum values instead of enum members
    )


class BaseResponseSchema(BaseSchema):
    """
    Base schema for entity responses.

    All entity response schemas should inherit from this class to ensure
    consistent fields across API responses. Mirrors model layer mixins
    (PublicIdMixin, TimestampMixin).

    Attributes
    ----------
    public_id : str
        Public UUID for external API use
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last update timestamp
    """

    public_id: str = Field(description="Public UUID identifier")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
