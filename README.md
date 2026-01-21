# FastAPI Backend Template

A **production-ready FastAPI backend template** following the MSCR (Model-Service-Controller-Repository) architecture pattern. This template provides a solid foundation for building scalable, maintainable backend applications.

## Features

- **Async SQLAlchemy 2.0** - Full async database support with type hints
- **JWT Authentication** - Access + refresh token rotation with family tracking
- **Argon2id Password Hashing** - OWASP-recommended password security
- **Pydantic v2 Validation** - Request/response schemas with strict typing
- **Repository Pattern** - Clean separation of data access logic
- **Dependency Injection** - FastAPI's native DI system
- **Alembic Migrations** - Async database migrations
- **Docker Ready** - Multi-stage Dockerfile and docker-compose
- **Comprehensive Testing** - pytest with async support

## Architecture

```
Controllers (Routers) → Services → Repositories → Models
       ↑                  ↑            ↑             ↑
    Schemas           Schemas      Session        Database
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Models** | `app/models/` | SQLAlchemy ORM models, database schema |
| **Schemas** | `app/schemas/` | Pydantic models for validation |
| **Routers** | `app/routers/` | FastAPI routes, HTTP handling |
| **Repositories** | `app/repositories/` | Database CRUD operations |
| **Services** | `app/services/` | Business logic, transaction control |

## Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI app factory
├── core/
│   ├── config.py        # Pydantic Settings
│   ├── dependencies.py  # Auth dependencies
│   ├── exceptions.py    # Custom exceptions
│   ├── responses.py     # Response helpers
│   └── security/        # JWT, password, encryption
├── routers/             # API endpoints
├── services/            # Business logic
├── repositories/        # Data access
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
└── db/                  # Database setup
```

## Quick Start

### Prerequisites

- Python 3.10+
- pip or uv

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd FastAPI-Backend-Template

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### Run Development Server

```bash
# Start the server
python run.py

# Or use uvicorn directly
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- Swagger docs: `http://localhost:8000/api/docs/swagger`
- ReDoc: `http://localhost:8000/api/docs/redoc`

### Initialize Database

```bash
# Create tables (development)
python cli.py init-db

# Seed with sample data
python cli.py seed
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (revoke token)
- `POST /api/v1/auth/logout-all` - Logout from all devices

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PATCH /api/v1/users/me` - Update profile
- `POST /api/v1/users/me/change-password` - Change password
- `DELETE /api/v1/users/me` - Delete account
- `GET /api/v1/users/{public_id}` - Get user by ID

### Items
- `GET /api/v1/items` - List items (paginated)
- `GET /api/v1/items/my` - List my items
- `GET /api/v1/items/search` - Search items
- `GET /api/v1/items/{public_id}` - Get item
- `POST /api/v1/items` - Create item
- `PATCH /api/v1/items/{public_id}` - Update item
- `DELETE /api/v1/items/{public_id}` - Delete item

### Health
- `GET /health` - Health check
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

## Configuration

Environment variables in `.env`:

```bash
# Application
APP_NAME="FastAPI Backend Template"
DEBUG=True

# Database (async SQLAlchemy)
DATABASE_URL=sqlite+aiosqlite:///./app.db
# For PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS
CORS_ORIGINS=*
```

## Docker

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
```

### Production Build

```bash
docker build -t fastapi-backend .
docker run -p 8000:8000 fastapi-backend
```

## Database Migrations

Using Alembic for migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## CLI Commands

```bash
python cli.py --help          # Show all commands
python cli.py init-db         # Create database tables
python cli.py seed            # Seed with sample data
python cli.py create-user     # Create user interactively
python cli.py list-users      # List all users
python cli.py cleanup-tokens  # Remove expired tokens
```

## Key Patterns

### Dual-ID Architecture

Models use integer primary keys internally and UUID for external API:

```python
# Internal: Fast JOINs
id: Mapped[int] = mapped_column(primary_key=True)

# External: Secure, no enumeration
public_id: Mapped[str] = mapped_column(String(36), unique=True)
```

### Transaction Control

Repositories flush, services commit:

```python
# Repository: flush() only
async def create(self, **kwargs):
    instance = self.model(**kwargs)
    self.session.add(instance)
    await self.flush()  # Stage changes
    return instance

# Service: commit() after business logic
async def register(self, data):
    user = await self.user_repo.create_user(...)
    await self.user_repo.commit()  # Service decides
    return user
```

### Dependency Injection

```python
# Define dependency
async def get_current_user(
    authorization: str = Header(...)
) -> TokenClaims:
    # Validate JWT
    ...

# Use in route
@router.get("/me")
async def get_profile(current_user: CurrentUser):
    return current_user
```

## Tech Stack

- **Framework:** FastAPI
- **Database:** SQLAlchemy 2.0 (async)
- **Validation:** Pydantic v2
- **Authentication:** PyJWT + Argon2
- **Testing:** pytest + httpx
- **Server:** Uvicorn

## License

MIT
