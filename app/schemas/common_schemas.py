"""
Common Pydantic schemas for pagination, errors, and generic responses.

This module defines reusable schemas used across multiple endpoints.
"""

from typing import Generic, TypeVar

from pydantic import Field

from app.schemas.base import BaseSchema

# Generic type variable for paginated responses
T = TypeVar("T")


class PaginationParams(BaseSchema):
    """
    Query parameters for pagination.

    Attributes
    ----------
    page : int
        Page number (1-indexed)
    per_page : int
        Number of items per page
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginationMeta(BaseSchema):
    """
    Pagination metadata for responses.

    Attributes
    ----------
    total : int
        Total number of items across all pages
    page : int
        Current page number
    per_page : int
        Number of items per page
    total_pages : int
        Total number of pages
    has_next : bool
        Whether there is a next page
    has_prev : bool
        Whether there is a previous page
    """

    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Has next page")
    has_prev: bool = Field(description="Has previous page")

    @classmethod
    def create(cls, total: int, page: int, per_page: int) -> "PaginationMeta":
        """
        Create pagination metadata from counts.

        Parameters
        ----------
        total : int
            Total number of items
        page : int
            Current page number
        per_page : int
            Items per page

        Returns
        -------
        PaginationMeta
            Computed pagination metadata
        """
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class PaginatedResponse(BaseSchema, Generic[T]):
    """
    Generic paginated response wrapper.

    Attributes
    ----------
    items : list[T]
        List of items for current page
    pagination : PaginationMeta
        Pagination metadata
    """

    items: list[T] = Field(description="Items for current page")
    pagination: PaginationMeta = Field(description="Pagination metadata")


class MessageResponse(BaseSchema):
    """
    Simple message response.

    Attributes
    ----------
    message : str
        Response message
    """

    message: str = Field(description="Response message")


class ValidationErrorDetail(BaseSchema):
    """
    Field-level validation error details.

    Attributes
    ----------
    field : str
        Field name that failed validation
    message : str
        Validation error message
    """

    field: str = Field(description="Field name")
    message: str = Field(description="Error message")


class ErrorResponse(BaseSchema):
    """
    Standard error response format.

    Attributes
    ----------
    message : str
        Error message
    errors : list[ValidationErrorDetail] | None
        Optional list of field-specific validation errors
    """

    message: str = Field(description="Error message")
    errors: list[ValidationErrorDetail] | None = Field(
        default=None, description="Field validation errors"
    )
