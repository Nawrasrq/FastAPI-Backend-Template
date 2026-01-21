"""
CLI commands using Typer.

This module provides command-line tools for database management,
user creation, and other administrative tasks.

Usage:
    python cli.py --help
    python cli.py seed
    python cli.py create-user
    python cli.py list-users
"""

import asyncio
from functools import wraps
from typing import Callable

import typer

app = typer.Typer(
    name="fastapi-cli",
    help="FastAPI Backend Template CLI",
    add_completion=False,
)


def async_command(f: Callable):
    """Decorator to run async functions in typer commands."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@app.command()
@async_command
async def seed():
    """
    Seed the database with initial data.

    Creates sample users and items for development/testing.
    """
    from app.db.session import AsyncSessionLocal, init_db
    from app.repositories.item_repository import ItemRepository
    from app.repositories.user_repository import UserRepository

    typer.echo("Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        item_repo = ItemRepository(session)

        # Check if admin user exists
        admin = await user_repo.find_by_email("admin@example.com")
        if admin:
            typer.echo("Database already seeded (admin user exists)")
            return

        # Create admin user
        typer.echo("Creating admin user...")
        admin = await user_repo.create_user(
            email="admin@example.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
        )
        admin.role = "admin"
        await user_repo.flush()

        # Create test user
        typer.echo("Creating test user...")
        test_user = await user_repo.create_user(
            email="test@example.com",
            password="Test123!",
            first_name="Test",
            last_name="User",
        )

        # Create sample items
        typer.echo("Creating sample items...")
        await item_repo.create_item(
            name="Sample Item 1",
            description="This is a sample item",
            owner_id=test_user.id,
        )
        await item_repo.create_item(
            name="Sample Item 2",
            description="Another sample item",
            owner_id=test_user.id,
        )

        await session.commit()

    typer.echo(typer.style("Database seeded successfully!", fg=typer.colors.GREEN))
    typer.echo("\nCreated users:")
    typer.echo("  - admin@example.com / Admin123!")
    typer.echo("  - test@example.com / Test123!")


@app.command()
@async_command
async def create_user(
    email: str = typer.Option(..., prompt=True, help="User email"),
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, confirmation_prompt=True, help="User password"
    ),
    first_name: str = typer.Option(..., prompt=True, help="First name"),
    last_name: str = typer.Option(..., prompt=True, help="Last name"),
    admin: bool = typer.Option(False, "--admin", help="Create as admin user"),
):
    """
    Create a new user interactively.

    Prompts for email, password, first name, and last name.
    """
    from app.db.session import AsyncSessionLocal, init_db
    from app.repositories.user_repository import UserRepository

    await init_db()

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)

        # Check if user exists
        existing = await user_repo.find_by_email(email)
        if existing:
            typer.echo(
                typer.style(f"User with email {email} already exists!", fg=typer.colors.RED)
            )
            raise typer.Exit(1)

        # Create user
        user = await user_repo.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        if admin:
            user.role = "admin"
            await user_repo.flush()

        await session.commit()

    typer.echo(typer.style(f"Created user: {email}", fg=typer.colors.GREEN))
    if admin:
        typer.echo("  Role: admin")


@app.command()
@async_command
async def list_users():
    """
    List all users in the database.
    """
    from app.db.session import AsyncSessionLocal, init_db
    from app.repositories.user_repository import UserRepository

    await init_db()

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        users = await user_repo.get_all(limit=100)

        if not users:
            typer.echo("No users found")
            return

        typer.echo(f"\nFound {len(users)} users:\n")
        typer.echo(f"{'ID':<5} {'Email':<30} {'Name':<25} {'Role':<12} {'Active'}")
        typer.echo("-" * 85)

        for user in users:
            active = typer.style("Yes", fg=typer.colors.GREEN) if user.is_active else typer.style("No", fg=typer.colors.RED)
            typer.echo(
                f"{user.id:<5} {user.email:<30} {user.full_name:<25} {user.role.value:<12} {active}"
            )


@app.command()
@async_command
async def init_db():
    """
    Initialize database tables.

    Creates all tables defined in the models.
    For production, use Alembic migrations instead.
    """
    from app.db.session import init_db as _init_db

    typer.echo("Creating database tables...")
    await _init_db()
    typer.echo(typer.style("Database initialized!", fg=typer.colors.GREEN))


@app.command()
@async_command
async def cleanup_tokens():
    """
    Clean up expired refresh tokens.

    Removes all expired tokens from the database.
    Run this periodically (e.g., daily cron job).
    """
    from app.db.session import AsyncSessionLocal
    from app.repositories.refresh_token_repository import RefreshTokenRepository

    async with AsyncSessionLocal() as session:
        token_repo = RefreshTokenRepository(session)
        count = await token_repo.cleanup_expired()

    typer.echo(typer.style(f"Cleaned up {count} expired tokens", fg=typer.colors.GREEN))


if __name__ == "__main__":
    app()
