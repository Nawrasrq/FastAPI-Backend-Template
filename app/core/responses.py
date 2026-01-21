"""
Standardized API response helpers for FastAPI.

This module provides helper functions for creating consistent
API response formats throughout the application.
"""

from datetime import datetime, timezone
from typing import Any


def success_response(data: Any = None) -> dict:
    """
    Create a standardized success response body.

    Parameters
    ----------
    data : Any, optional
        Response data to include

    Returns
    -------
    dict
        Standardized success response

    Notes
    -----
    Unlike Flask, the status code is set at the route level in FastAPI
    using the `status_code` parameter or `Response` object.

    Example
    -------
    ```python
    @router.get("/items")
    async def list_items():
        items = await get_items()
        return success_response({"items": items})

    @router.post("/items", status_code=status.HTTP_201_CREATED)
    async def create_item(data: ItemCreate):
        item = await create_item(data)
        return success_response(item.model_dump())
    ```
    """
    return {
        "success": True,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def error_response(message: str, errors: dict | None = None) -> dict:
    """
    Create a standardized error response body.

    Parameters
    ----------
    message : str
        Error message
    errors : dict | None, optional
        Field-specific error details

    Returns
    -------
    dict
        Standardized error response

    Notes
    -----
    This is typically used by exception handlers, not directly in routes.

    Example
    -------
    ```python
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.message, errors=exc.payload),
        )
    ```
    """
    response = {
        "success": False,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if errors:
        response["errors"] = errors
    return response


def paginated_response(
    items: list[Any],
    page: int,
    per_page: int,
    total: int,
) -> dict:
    """
    Create a standardized paginated response.

    Parameters
    ----------
    items : list[Any]
        List of items for current page
    page : int
        Current page number (1-indexed)
    per_page : int
        Items per page
    total : int
        Total number of items

    Returns
    -------
    dict
        Standardized paginated response with metadata

    Example
    -------
    ```python
    @router.get("/items")
    async def list_items(page: int = 1, per_page: int = 20):
        items, total = await get_items_paginated(page, per_page)
        return paginated_response(
            items=[item.model_dump() for item in items],
            page=page,
            per_page=per_page,
            total=total,
        )
    ```
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "success": True,
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
