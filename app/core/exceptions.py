"""
Custom exception hierarchy for API error handling.

This module defines custom exceptions that map to HTTP status codes,
enabling consistent error responses throughout the application.
"""


class APIException(Exception):
    """
    Base exception for all API errors.

    All custom exceptions inherit from this class, enabling centralized
    exception handling in the FastAPI application.

    Parameters
    ----------
    message : str
        Error message to return to client
    status_code : int, optional
        HTTP status code (default: 500)
    payload : dict | None, optional
        Additional error details
    """

    def __init__(self, message: str, status_code: int = 500, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> dict:
        """
        Convert exception to dictionary for JSON response.

        Returns
        -------
        dict
            Dictionary with error details
        """
        rv = {"message": self.message, **self.payload}
        return rv


class ValidationError(APIException):
    """
    Validation error (400 Bad Request).

    Raised when request data fails validation.

    Parameters
    ----------
    message : str
        Validation error message
    payload : dict | None, optional
        Field-specific validation errors
    """

    def __init__(self, message: str = "Validation failed", payload: dict | None = None):
        super().__init__(message, status_code=400, payload=payload)


class UnauthorizedError(APIException):
    """
    Authentication error (401 Unauthorized).

    Raised when authentication is required but not provided or invalid.

    Parameters
    ----------
    message : str
        Authentication error message
    """

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class ForbiddenError(APIException):
    """
    Authorization error (403 Forbidden).

    Raised when user is authenticated but lacks required permissions.

    Parameters
    ----------
    message : str
        Authorization error message
    """

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class NotFoundError(APIException):
    """
    Resource not found error (404 Not Found).

    Raised when requested resource does not exist.

    Parameters
    ----------
    message : str
        Not found error message
    resource : str | None, optional
        Resource type that was not found
    """

    def __init__(self, message: str = "Resource not found", resource: str | None = None):
        payload = {"resource": resource} if resource else {}
        super().__init__(message, status_code=404, payload=payload)


class ConflictError(APIException):
    """
    Resource conflict error (409 Conflict).

    Raised when operation conflicts with existing resource (e.g., duplicate email).

    Parameters
    ----------
    message : str
        Conflict error message
    field : str | None, optional
        Field that caused the conflict
    """

    def __init__(self, message: str = "Resource conflict", field: str | None = None):
        payload = {"field": field} if field else {}
        super().__init__(message, status_code=409, payload=payload)


class InternalServerError(APIException):
    """
    Internal server error (500 Internal Server Error).

    Raised for unexpected errors.

    Parameters
    ----------
    message : str
        Error message
    """

    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(message, status_code=500)
