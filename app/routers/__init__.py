"""
FastAPI routers for API endpoints.

This module exports all routers for registration in the main application.
"""

from app.routers import auth, health, items, users

__all__ = [
    "auth",
    "health",
    "items",
    "users",
]
