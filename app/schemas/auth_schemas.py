"""
Pydantic schemas for authentication.

This module defines request and response schemas for authentication operations.
"""

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    """
    Schema for login request.

    Attributes
    ----------
    email : EmailStr
        User email address
    password : str
        User password
    """

    email: EmailStr = Field(description="Email address")
    password: str = Field(description="Password")


class TokenResponse(BaseSchema):
    """
    Schema for token response.

    Attributes
    ----------
    access_token : str
        JWT access token
    refresh_token : str
        JWT refresh token
    token_type : str
        Token type (always "Bearer")
    expires_in : int
        Access token expiration time in seconds
    """

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(description="Seconds until access token expires")


class RefreshRequest(BaseSchema):
    """
    Schema for refresh token request.

    Attributes
    ----------
    refresh_token : str
        Refresh token to rotate
    """

    refresh_token: str = Field(description="Refresh token")


class PasswordResetRequest(BaseSchema):
    """
    Schema for password reset request.

    Attributes
    ----------
    email : EmailStr
        User email address
    """

    email: EmailStr = Field(description="Email address")


class PasswordChangeRequest(BaseSchema):
    """
    Schema for password change request.

    Attributes
    ----------
    old_password : str
        Current password
    new_password : str
        New password
    """

    old_password: str = Field(description="Current password")
    new_password: str = Field(description="New password")
