"""
Core utilities and configuration for the application.
"""

from app.core.config import settings
from app.core.dependencies import CurrentUser, CurrentUserId, OptionalUser
from app.core.exceptions import (
    APIException,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.responses import error_response, paginated_response, success_response

__all__ = [
    # Config
    "settings",
    # Dependencies
    "CurrentUser",
    "CurrentUserId",
    "OptionalUser",
    # Exceptions
    "APIException",
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "InternalServerError",
    # Responses
    "success_response",
    "error_response",
    "paginated_response",
]
