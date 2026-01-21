"""
JWT token management with refresh token rotation.

This module provides secure JWT token generation and validation
with support for access/refresh token pairs and token rotation.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenClaims(BaseModel):
    """
    JWT token claims with strict typing.

    Attributes
    ----------
    sub : str
        Subject (user ID as string)
    iat : datetime
        Issued at timestamp
    exp : datetime
        Expiration timestamp
    jti : str
        Unique token ID (for revocation)
    type : Literal["access", "refresh"]
        Token type
    email : str
        User's email address
    role : str | None
        User's role name
    is_super_admin : bool
        Whether user has super admin privileges
    permissions : list[str]
        List of permission strings (access tokens only)
    """

    # Standard claims
    sub: str
    iat: datetime
    exp: datetime
    jti: str

    # Custom claims
    type: Literal["access", "refresh"]
    email: str

    # Role and permissions
    role: str | None = None
    is_super_admin: bool = False
    permissions: list[str] = []


class TokenPair(BaseModel):
    """
    Access and refresh token pair.

    Attributes
    ----------
    access_token : str
        Short-lived JWT access token
    refresh_token : str
        Long-lived JWT refresh token
    token_type : str
        Token type (always "Bearer")
    expires_in : int
        Seconds until access token expires
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class TokenService:
    """
    JWT token management following security best practices.

    Security features:
    - Short-lived access tokens (15 min default)
    - Refresh token rotation with family tracking
    - Token ID (jti) for revocation checking

    Notes
    -----
    This is a synchronous service because JWT operations are CPU-bound
    and very fast. FastAPI will run it in a thread pool if needed.
    """

    def __init__(self) -> None:
        """Initialize TokenService with settings."""
        self._secret = settings.JWT_SECRET_KEY.get_secret_value()
        self._algorithm = settings.JWT_ALGORITHM
        self._access_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self,
        user_id: int,
        email: str,
        permissions: list[str] | None = None,
        role: str | None = None,
        is_super_admin: bool = False,
    ) -> tuple[str, datetime]:
        """
        Create a short-lived access token.

        Parameters
        ----------
        user_id : int
            User's internal ID
        email : str
            User's email address
        permissions : list[str] | None, optional
            List of permission strings
        role : str | None, optional
            User's role name
        is_super_admin : bool, optional
            Whether user has super admin privileges

        Returns
        -------
        tuple[str, datetime]
            Tuple of (token, expiration_datetime)
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self._access_expire_minutes)

        claims = TokenClaims(
            sub=str(user_id),
            iat=now,
            exp=expires,
            jti=secrets.token_urlsafe(16),
            type="access",
            email=email,
            role=role,
            is_super_admin=is_super_admin,
            permissions=permissions or [],
        )

        # Convert to dict and use timestamps for iat/exp (JWT standard)
        payload = claims.model_dump()
        payload["iat"] = int(now.timestamp())
        payload["exp"] = int(expires.timestamp())

        token = jwt.encode(
            payload,
            self._secret,
            algorithm=self._algorithm,
        )

        return token, expires

    def create_refresh_token(
        self,
        user_id: int,
        email: str,
        token_family: str | None = None,
    ) -> tuple[str, str, str, datetime]:
        """
        Create a long-lived refresh token.

        Parameters
        ----------
        user_id : int
            User's internal ID
        email : str
            User's email address
        token_family : str | None, optional
            Token family for rotation tracking

        Returns
        -------
        tuple[str, str, str, datetime]
            Tuple of (token, token_hash, token_family, expiration_datetime)

        Notes
        -----
        The token_hash is stored in database, never the raw token.
        token_family groups related tokens for rotation tracking.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=self._refresh_expire_days)

        jti = secrets.token_urlsafe(32)

        if token_family is None:
            token_family = secrets.token_hex(16)

        claims = TokenClaims(
            sub=str(user_id),
            iat=now,
            exp=expires,
            jti=jti,
            type="refresh",
            email=email,
        )

        # Convert to dict and use timestamps for iat/exp (JWT standard)
        payload = claims.model_dump()
        payload["iat"] = int(now.timestamp())
        payload["exp"] = int(expires.timestamp())

        token = jwt.encode(
            payload,
            self._secret,
            algorithm=self._algorithm,
        )

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        return token, token_hash, token_family, expires

    def decode_token(self, token: str, token_type: Literal["access", "refresh"]) -> TokenClaims:
        """
        Decode and validate a JWT token.

        Parameters
        ----------
        token : str
            JWT token string
        token_type : Literal["access", "refresh"]
            Expected token type

        Returns
        -------
        TokenClaims
            Validated token claims

        Raises
        ------
        jwt.InvalidTokenError
            If token is invalid, expired, or wrong type
        """
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={
                    "require": ["sub", "iat", "exp", "jti", "type"],
                    "verify_exp": True,
                    "verify_iat": True,
                },
            )

            # Convert numeric timestamps back to datetime for TokenClaims
            if isinstance(payload.get("iat"), int | float):
                payload["iat"] = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
            if isinstance(payload.get("exp"), int | float):
                payload["exp"] = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

            claims = TokenClaims(**payload)

            if claims.type != token_type:
                raise jwt.InvalidTokenError(f"Expected {token_type} token, got {claims.type}")

            return claims

        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired") from None
        except jwt.InvalidTokenError:
            raise
        except Exception as e:
            raise jwt.InvalidTokenError(f"Invalid token: {e}") from None

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash a token for storage comparison.

        Parameters
        ----------
        token : str
            Raw token string

        Returns
        -------
        str
            SHA256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()


# Singleton instance
token_service = TokenService()
