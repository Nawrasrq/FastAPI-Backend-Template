"""
FastAPI dependencies for authentication and authorization.

This module provides dependency injection functions that replace
Flask's @require_auth decorator pattern. Dependencies are the FastAPI
way to handle cross-cutting concerns like authentication.

Usage
-----
```python
from app.core.dependencies import CurrentUser, CurrentUserId

@router.get("/me")
async def get_profile(current_user: CurrentUser):
    # current_user is the validated TokenClaims
    return {"email": current_user.email}

@router.get("/my-items")
async def get_my_items(user_id: CurrentUserId):
    # user_id is the integer user ID
    return await get_items_by_user(user_id)
```
"""

import logging
from typing import Annotated

import jwt
from fastapi import Depends, Header

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security.jwt import TokenClaims, token_service

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> TokenClaims:
    """
    Dependency to extract and validate JWT from Authorization header.

    This replaces Flask's @require_auth decorator pattern.

    Parameters
    ----------
    authorization : str | None
        Authorization header value (automatically extracted by FastAPI)

    Returns
    -------
    TokenClaims
        Validated token claims containing user information

    Raises
    ------
    UnauthorizedError
        If token is missing, invalid, or expired

    Example
    -------
    ```python
    @router.get("/protected")
    async def protected_route(current_user: TokenClaims = Depends(get_current_user)):
        return {"user_id": current_user.sub}
    ```
    """
    if not authorization:
        logger.warning("Missing Authorization header")
        raise UnauthorizedError(message="Authorization header is required")

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning("Invalid Authorization header format")
        raise UnauthorizedError(message="Invalid Authorization header format. Use: Bearer <token>")

    token = parts[1]

    try:
        claims = token_service.decode_token(token, "access")
    except jwt.ExpiredSignatureError:
        logger.warning("Expired access token")
        raise UnauthorizedError(message="Token has expired") from None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid access token: {e}")
        raise UnauthorizedError(message="Invalid token") from None

    logger.debug(f"Authenticated user: {claims.sub}")
    return claims


# Type alias for cleaner route signatures
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


async def get_current_user_id(current_user: CurrentUser) -> int:
    """
    Dependency to get current user's ID as integer.

    Parameters
    ----------
    current_user : TokenClaims
        Current user's token claims (injected)

    Returns
    -------
    int
        User's internal ID

    Example
    -------
    ```python
    @router.get("/my-items")
    async def get_my_items(user_id: int = Depends(get_current_user_id)):
        return await get_items_by_user(user_id)
    ```
    """
    return int(current_user.sub)


# Type alias for cleaner route signatures
CurrentUserId = Annotated[int, Depends(get_current_user_id)]


def require_permission(permission: str):
    """
    Dependency factory for permission-based authorization.

    Creates a dependency that checks if the current user has the
    required permission. Super admins bypass permission checks.

    Parameters
    ----------
    permission : str
        Required permission string (e.g., "items:write", "admin:manage")

    Returns
    -------
    Callable
        Dependency function that validates the permission

    Example
    -------
    ```python
    @router.delete("/admin/users/{user_id}")
    async def delete_user(
        user_id: str,
        current_user: CurrentUser,
        _: None = Depends(require_permission("admin:delete_users")),
    ):
        # Only users with admin:delete_users permission can access
        ...
    ```
    """

    async def permission_checker(current_user: CurrentUser) -> None:
        # Super admins bypass permission checks
        if current_user.is_super_admin:
            logger.debug(f"Super admin access granted for: {permission}")
            return

        if permission not in current_user.permissions:
            logger.warning(f"Permission denied for user {current_user.sub}: {permission}")
            raise ForbiddenError(message=f"Permission required: {permission}")

        logger.debug(f"Permission granted for user {current_user.sub}: {permission}")

    return permission_checker


def require_role(role: str):
    """
    Dependency factory for role-based authorization.

    Creates a dependency that checks if the current user has the
    required role. Super admins bypass role checks.

    Parameters
    ----------
    role : str
        Required role (e.g., "admin", "super_admin")

    Returns
    -------
    Callable
        Dependency function that validates the role

    Example
    -------
    ```python
    @router.get("/admin/dashboard")
    async def admin_dashboard(
        current_user: CurrentUser,
        _: None = Depends(require_role("admin")),
    ):
        # Only admins can access
        ...
    ```
    """

    async def role_checker(current_user: CurrentUser) -> None:
        # Super admins have all roles
        if current_user.is_super_admin:
            logger.debug(f"Super admin access granted for role: {role}")
            return

        if current_user.role != role:
            logger.warning(
                f"Role check failed for user {current_user.sub}: "
                f"required={role}, actual={current_user.role}"
            )
            raise ForbiddenError(message=f"Role required: {role}")

        logger.debug(f"Role check passed for user {current_user.sub}: {role}")

    return role_checker


async def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
) -> TokenClaims | None:
    """
    Dependency for routes that work with or without authentication.

    Returns the user claims if a valid token is provided, otherwise None.
    Does not raise an error for missing/invalid tokens.

    Parameters
    ----------
    authorization : str | None
        Authorization header value

    Returns
    -------
    TokenClaims | None
        User claims if authenticated, None otherwise

    Example
    -------
    ```python
    @router.get("/items/{item_id}")
    async def get_item(
        item_id: str,
        current_user: TokenClaims | None = Depends(get_optional_user),
    ):
        item = await get_item(item_id)
        # Show extra info if user is authenticated
        if current_user:
            item["is_owner"] = item.owner_id == int(current_user.sub)
        return item
    ```
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    try:
        return token_service.decode_token(token, "access")
    except jwt.InvalidTokenError:
        return None


# Type alias for optional user
OptionalUser = Annotated[TokenClaims | None, Depends(get_optional_user)]
