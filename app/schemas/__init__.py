"""
Pydantic schemas for request/response validation.

This module exports all schemas for easy importing:
    from app.schemas import UserRegister, UserResponse, LoginRequest
"""

from app.schemas.auth_schemas import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.base import BaseResponseSchema, BaseSchema
from app.schemas.common_schemas import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    ValidationErrorDetail,
)
from app.schemas.item_schemas import ItemCreate, ItemResponse, ItemUpdate
from app.schemas.user_schemas import UserRegister, UserResponse, UserUpdate

__all__ = [
    # Base
    "BaseSchema",
    "BaseResponseSchema",
    # Auth
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "PasswordResetRequest",
    "PasswordChangeRequest",
    # User
    "UserRegister",
    "UserUpdate",
    "UserResponse",
    # Item
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    # Common
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "MessageResponse",
    "ValidationErrorDetail",
    "ErrorResponse",
]
