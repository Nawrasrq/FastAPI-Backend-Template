"""
Health check router for application monitoring.

This module provides health check endpoints for load balancers,
container orchestration, and monitoring systems.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.responses import success_response

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns a simple status response indicating the application is running.
    Used by load balancers and container health checks.

    Returns
    -------
    dict
        Health status response
    """
    return success_response(
        {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check endpoint.

    Indicates whether the application is ready to receive traffic.
    Can include database connectivity checks in a real application.

    Returns
    -------
    dict
        Readiness status response
    """
    # In a real application, you might check:
    # - Database connectivity
    # - Cache connectivity
    # - External service availability
    return success_response(
        {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint.

    Indicates whether the application is alive and should not be restarted.
    A simple response is sufficient - if it responds, it's alive.

    Returns
    -------
    dict
        Liveness status response
    """
    return success_response(
        {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
