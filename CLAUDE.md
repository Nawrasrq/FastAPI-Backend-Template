# CLAUDE.md - AI Context for FastAPI Backend Template

This file provides context for AI assistants (Claude, GPT, etc.) when working with this FastAPI backend template. It describes the architecture, patterns, and conventions used throughout the codebase.

## Project Overview

This is a **production-ready FastAPI backend template** following the MSCR (Model-Service-Controller-Repository) architecture pattern. It's designed to be extended into specific backend applications.

### Tech Stack

- **Framework:** FastAPI with async support
- **ORM:** SQLAlchemy 2.0 async with type hints (`Mapped[]`, `mapped_column()`)
- **Validation:** Pydantic v2 for request/response schemas
- **Authentication:** JWT with refresh token rotation
- **Password Hashing:** Argon2id (OWASP recommended)
- **Database:** PostgreSQL (asyncpg) or SQLite (aiosqlite) for development
- **Testing:** pytest with pytest-asyncio

## Architecture: MSCR Pattern

```
Routers (HTTP) → Services (Business Logic) → Repositories (Data Access) → Models (ORM)
     ↑                    ↑                          ↑                         ↑
  Schemas              Schemas                  AsyncSession                Database
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Models** | `app/models/` | SQLAlchemy ORM models, database schema |
| **Schemas** | `app/schemas/` | Pydantic models for validation |
| **Routers** | `app/routers/` | FastAPI routes, HTTP handling |
| **Repositories** | `app/repositories/` | Database CRUD operations |
| **Services** | `app/services/` | Business logic, transaction control |

### Transaction Control Pattern

**Critical:** Services control transaction boundaries, repositories handle database operations.

```python
# Repository: flush() only (tactical)
async def create(self, **kwargs) -> ModelType:
    instance = self.model(**kwargs)
    self.session.add(instance)
    await self.flush()  # Stage changes, get ID
    return instance

# Service: commit() after business logic (strategic)
async def register_user(self, data: UserRegister) -> TokenResponse:
    user = await self.user_repo.create_user(**data.model_dump())
    await self.user_repo.commit()  # Service decides when to commit
    return self._create_token_response(user)
```

## Key Patterns & Conventions

### 1. Dual-ID Architecture

All models use integer primary keys internally + UUID for external API exposure:

```python
# Internal: Integer PK (4 bytes, fast JOINs)
id: Mapped[int] = mapped_column(primary_key=True)

# External: UUID (prevents enumeration attacks)
public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
```

**API Pattern:**
- External endpoints use `public_id` (UUID)
- Internal operations use `id` (integer)
- Never expose integer IDs in API responses

### 2. Model Mixins

Located in `app/models/base.py`:

| Mixin | Fields | Usage |
|-------|--------|-------|
| `PublicIdMixin` | `public_id` | Add to models exposed via API |
| `TimestampMixin` | `created_at`, `updated_at` | Add to all models |
| `SoftDeleteMixin` | `is_deleted`, `deleted_at` | Inherited from Base |

```python
class User(Base, TimestampMixin, PublicIdMixin):
    # Inherits: id, public_id, created_at, updated_at, is_deleted, deleted_at
    email: Mapped[str] = mapped_column(String(255), unique=True)
```

### 3. Async SQLAlchemy

This template uses async SQLAlchemy 2.0:

```python
# Session creation
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### 4. FastAPI Dependencies (Replaces Flask Decorators)

Flask's `@require_auth` decorator becomes a FastAPI dependency:

```python
# app/core/dependencies.py
async def get_current_user(
    authorization: Annotated[str | None, Header()] = None
) -> TokenClaims:
    # Validate JWT and return claims
    ...

# Type alias for cleaner signatures
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]

# Usage in router
@router.get("/me")
async def get_profile(current_user: CurrentUser):
    return success_response(current_user)
```

### 5. Enum Pattern

Use `str, PyEnum` for API-friendly enums:

```python
from enum import Enum as PyEnum

class ItemStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
```

Benefits: JSON serializable, string comparisons work, clean API responses.

### 6. Boolean Queries

```python
# ❌ Avoid
query.where(Model.is_deleted == False)

# ✅ Use
query.where(Model.is_deleted.is_(False))  # For False
query.where(Model.is_active)              # For True
```

### 7. Race Condition Prevention

For unique constraints, use check-then-catch pattern:

```python
async def create_user(self, email: str) -> User:
    try:
        # 1. Optimistic check (fast path)
        if await self.find_by_email(email):
            raise ConflictError("Email exists")

        # 2. Create with database constraint
        user = User(email=email)
        self.session.add(user)
        await self.flush()
        return user

    except IntegrityError:
        # 3. Safety net for race conditions
        await self.rollback()
        raise ConflictError("Email exists")
```

## File Structure

```
app/
├── __init__.py          # Package init
├── main.py              # FastAPI app factory
├── core/
│   ├── config.py        # Pydantic Settings (env vars)
│   ├── dependencies.py  # Auth dependencies (CurrentUser, etc.)
│   ├── exceptions.py    # Custom API exceptions
│   ├── responses.py     # Response helpers
│   └── security/
│       ├── jwt.py       # JWT token service
│       ├── password.py  # Argon2 password service
│       └── encryption.py # Fernet encryption
├── routers/             # FastAPI routers (was controllers/)
│   ├── auth.py
│   ├── users.py
│   ├── items.py
│   └── health.py
├── services/            # Business logic
│   ├── auth_service.py
│   ├── user_service.py
│   └── item_service.py
├── repositories/        # Data access
│   ├── base.py          # Generic BaseRepository[T]
│   ├── user_repository.py
│   └── item_repository.py
├── models/              # SQLAlchemy models
│   ├── base.py          # Mixins + custom Base
│   ├── user.py
│   ├── item.py
│   └── refresh_token.py
├── schemas/             # Pydantic schemas
│   ├── base.py
│   ├── auth_schemas.py
│   ├── user_schemas.py
│   └── item_schemas.py
└── db/
    ├── session.py       # Async engine + session
    └── init_db.py       # Database initialization
```

## Adding New Features

### Adding a New Model

1. Create model in `app/models/new_model.py`:
```python
from app.models.base import Base, TimestampMixin, PublicIdMixin

class NewModel(Base, TimestampMixin, PublicIdMixin):
    __tablename__ = "new_models"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Add fields...
```

2. Export in `app/models/__init__.py`

3. Create migration: `alembic revision --autogenerate -m "Add new_model table"`

4. Apply migration: `alembic upgrade head`

### Adding a New Repository

1. Create `app/repositories/new_model_repository.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.new_model import NewModel

class NewModelRepository(BaseRepository[NewModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(NewModel, session)

    # Add custom queries...
```

### Adding a New Service

1. Create `app/services/new_model_service.py`:
```python
from app.repositories.new_model_repository import NewModelRepository
from app.schemas.new_model_schemas import NewModelCreate

class NewModelService:
    def __init__(self, repo: NewModelRepository):
        self.repo = repo

    async def create(self, data: NewModelCreate) -> NewModel:
        instance = await self.repo.create(**data.model_dump())
        await self.repo.commit()
        return instance
```

### Adding a New Router

1. Create `app/routers/new_models.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.core.responses import success_response
from app.db.session import get_db
from app.repositories.new_model_repository import NewModelRepository
from app.services.new_model_service import NewModelService
from app.schemas.new_model_schemas import NewModelCreate, NewModelResponse

router = APIRouter(prefix="/new-models", tags=["New Models"])

async def get_service(db: AsyncSession = Depends(get_db)) -> NewModelService:
    return NewModelService(NewModelRepository(db))

@router.post("", status_code=201)
async def create(
    data: NewModelCreate,
    current_user: CurrentUser,
    service: NewModelService = Depends(get_service),
):
    instance = await service.create(data)
    return success_response(NewModelResponse.model_validate(instance).model_dump())
```

2. Register router in `app/main.py`:
```python
from app.routers import new_models
app.include_router(new_models.router, prefix="/api/v1")
```

## Common Operations

### Authentication Flow

```python
# Login: POST /api/v1/auth/login
# Returns: { access_token, refresh_token, token_type, expires_in }

# Use access token in header:
Authorization: Bearer <access_token>

# Refresh: POST /api/v1/auth/refresh
# Body: { refresh_token }
# Returns: New token pair (old refresh token is revoked)
```

### Database Commands

```bash
# Initialize database
python cli.py init-db

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Seed database
python cli.py seed

# Create user interactively
python cli.py create-user

# List users
python cli.py list-users
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test
pytest tests/test_auth.py::test_login_success -v
```

## Security Considerations

1. **Never expose integer IDs** - Use `public_id` (UUID) in API responses
2. **Password requirements** - Minimum 8 characters (configurable via `PASSWORD_MIN_LENGTH`)
3. **JWT tokens** - Short-lived access tokens (15 min), long-lived refresh tokens (30 days)
4. **Refresh token rotation** - Old tokens are revoked on refresh
5. **Token families** - Detect refresh token reuse attacks
6. **Database constraints** - Always add `unique=True` for uniqueness requirements

## Environment Variables

Key variables in `.env`:

```bash
# Required
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# Optional (have defaults)
DEBUG=True
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

## Extending This Template

When building a specific application from this template:

1. **Keep the MSCR pattern** - Add new models/services/routers following existing patterns
2. **Use mixins** - Compose models from existing mixins for consistency
3. **Add domain-specific services** - Business logic goes in services, not routers
4. **Extend schemas** - Add validation rules in Pydantic schemas
5. **Add tests** - Follow the test patterns in `tests/` directory
6. **Update OpenAPI docs** - FastAPI automatically generates Swagger documentation

## Type Hints Reference

```python
# SQLAlchemy 2.0 style
from sqlalchemy.orm import Mapped, mapped_column

# Mapped column
name: Mapped[str] = mapped_column(String(100))

# Optional column
description: Mapped[str | None] = mapped_column(String(500), nullable=True)

# Foreign key
user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

# Relationship
user: Mapped["User"] = relationship(back_populates="items")
items: Mapped[list["Item"]] = relationship(back_populates="user")
```

## Flask vs FastAPI Mapping

| Flask | FastAPI |
|-------|---------|
| `Blueprint("auth", ...)` | `APIRouter(prefix="/auth", tags=["Auth"])` |
| `@bp.route("/path", methods=["POST"])` | `@router.post("/path")` |
| `@require_auth` decorator | `current_user: CurrentUser` dependency |
| `request.get_json()` | `data: Schema` parameter (auto-parsed) |
| `return jsonify(data), 201` | `return data` + `status_code=201` |
| `db.session` (Flask-SQLAlchemy) | `AsyncSession` via `Depends(get_db)` |
| `flask db migrate` | `alembic revision --autogenerate` |
| `gunicorn` | `uvicorn` |

## Troubleshooting

### Common Issues

1. **Import errors with async session**: Ensure you're using `AsyncSession` from `sqlalchemy.ext.asyncio`
2. **Type checker errors on relationships**: Use `TYPE_CHECKING` for forward references
3. **Test isolation issues**: Tests use function-scoped fixtures that create/drop tables
4. **Migration conflicts**: Delete migration files and recreate if schema changes significantly during development
5. **Async context errors**: Ensure all database operations use `await`
