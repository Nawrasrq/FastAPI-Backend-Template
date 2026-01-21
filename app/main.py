"""
FastAPI application factory.

This module creates and configures the FastAPI application using
lifespan events for startup/shutdown, enabling flexible configuration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import APIException
from app.core.responses import error_response
from app.routers import auth, health, items, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    Replaces Flask's before_first_request pattern.
    Use this for database connection setup, cache warming, etc.
    """
    # Startup
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.APP_NAME}")

    # Initialize database tables (for development)
    # In production, use Alembic migrations instead
    if settings.DEBUG:
        from app.db.session import init_db

        await init_db()
        logger.info("Database tables created (development mode)")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns
    -------
    FastAPI
        Configured FastAPI application instance
    """
    # Configure logging
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize FastAPI
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        openapi_url="/api/docs/openapi.json" if settings.DEBUG else None,
        docs_url="/api/docs/swagger" if settings.DEBUG else None,
        redoc_url="/api/docs/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(items.router, prefix="/api/v1")

    # Register exception handlers
    register_exception_handlers(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register custom exception handlers.

    Parameters
    ----------
    app : FastAPI
        FastAPI application instance
    """

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.message, errors=exc.payload if exc.payload else None),
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(request: Request, exc: PydanticValidationError):
        """Handle Pydantic validation errors."""
        errors = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors[field] = error["msg"]

        return JSONResponse(
            status_code=422,
            content=error_response("Validation failed", errors=errors),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger = logging.getLogger(__name__)
        logger.exception(f"Unexpected error: {exc}")

        # Don't expose internal errors in production
        message = str(exc) if settings.DEBUG else "An unexpected error occurred"

        return JSONResponse(
            status_code=500,
            content=error_response(message),
        )


# Create application instance
app = create_app()
