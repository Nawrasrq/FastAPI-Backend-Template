"""
Pydantic schemas for User model.

This module defines request and response schemas for user operations.
"""

from pydantic import EmailStr, Field, field_validator

from app.core.config import settings
from app.schemas.base import BaseResponseSchema, BaseSchema


class UserRegister(BaseSchema):
    """
    Schema for user registration.

    Attributes
    ----------
    email : EmailStr
        Valid email address
    password : str
        Password (min length from settings)
    first_name : str
        First name
    last_name : str
        Last name
    """

    email: EmailStr = Field(description="Email address")
    password: str = Field(min_length=settings.PASSWORD_MIN_LENGTH, description="Password")
    first_name: str = Field(min_length=1, max_length=100, description="First name")
    last_name: str = Field(min_length=1, max_length=100, description="Last name")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets strength requirements.

        Parameters
        ----------
        v : str
            Password to validate

        Returns
        -------
        str
            Validated password

        Raises
        ------
        ValueError
            If password fails validation
        """
        from app.core.security.password import password_service

        is_valid, violations = password_service.validate_strength(v)
        if not is_valid:
            raise ValueError("; ".join(violations))
        return v


class UserUpdate(BaseSchema):
    """
    Schema for updating user profile.

    All fields are optional.

    Attributes
    ----------
    first_name : str | None
        First name
    last_name : str | None
        Last name
    """

    first_name: str | None = Field(
        default=None, min_length=1, max_length=100, description="First name"
    )
    last_name: str | None = Field(
        default=None, min_length=1, max_length=100, description="Last name"
    )


class UserResponse(BaseResponseSchema):
    """
    Schema for user response (excludes password_hash).

    Attributes
    ----------
    email : str
        Email address
    first_name : str
        First name
    last_name : str
        Last name
    is_active : bool
        Account active status
    role : str
        User role
    """

    email: str = Field(description="Email address")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    is_active: bool = Field(description="Active status")
    role: str = Field(description="User role")
