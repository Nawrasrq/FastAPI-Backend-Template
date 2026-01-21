"""
Pytest configuration and fixtures for FastAPI testing.

This module provides fixtures for:
- Async database sessions with transaction rollback
- Test client with database override
- Sample users and authentication headers
"""

import os

# Set testing environment BEFORE importing app modules
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DEBUG"] = "true"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security.jwt import token_service
from app.db.session import get_db
from app.main import app
from app.models import Base, User


# Create test engine (in-memory SQLite)
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for pytest-asyncio."""
    return "asyncio"


@pytest.fixture(scope="function")
async def db_session():
    """
    Provide a transactional database session for each test.

    Creates tables before test, yields session, then rolls back and drops tables.
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestAsyncSessionLocal() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession):
    """
    Provide async test client with database override.

    Uses httpx.AsyncClient for async request handling.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create a test user.

    Returns a user with:
    - email: test@example.com
    - password: TestPassword123!
    """
    user = User(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        hashed_password="",
    )
    user.set_password("TestPassword123!")

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """
    Create an admin test user.

    Returns a user with:
    - email: admin@example.com
    - password: AdminPassword123!
    - role: admin
    """
    from app.models.user import UserRole

    user = User(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        hashed_password="",
        role=UserRole.ADMIN,
    )
    user.set_password("AdminPassword123!")

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """
    Generate authentication headers for test user.

    Returns headers with Bearer token for authenticated requests.
    """
    access_token, _ = token_service.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        role=test_user.role.value if test_user.role else None,
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    """
    Generate authentication headers for admin user.
    """
    access_token, _ = token_service.create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        role=admin_user.role.value if admin_user.role else None,
        is_super_admin=admin_user.is_super_admin,
    )
    return {"Authorization": f"Bearer {access_token}"}
