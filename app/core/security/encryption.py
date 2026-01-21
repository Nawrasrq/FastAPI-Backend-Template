"""
Encryption service for sensitive data.

This module provides Fernet-based symmetric encryption for storing
sensitive data like API tokens or other secrets that need to be retrieved.
"""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


class EncryptionService:
    """
    Fernet-based encryption for sensitive data.

    Uses PBKDF2 to derive encryption key from application secret.
    All encrypted values are base64-encoded strings.

    Notes
    -----
    Use this for data that needs to be decrypted later (e.g., API tokens).
    For passwords, use PasswordService (one-way hashing) instead.
    """

    # Salt for key derivation (application-specific)
    _SALT = b"fastapi_template_encryption_v1"

    def __init__(self) -> None:
        """Initialize EncryptionService with derived Fernet key."""
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """
        Derive Fernet key from application encryption key.

        Returns
        -------
        Fernet
            Configured Fernet instance
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._SALT,
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(settings.ENCRYPTION_KEY.get_secret_value().encode())
        )
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        Parameters
        ----------
        plaintext : str
            The string to encrypt

        Returns
        -------
        str
            Base64-encoded ciphertext
        """
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a base64-encoded ciphertext.

        Parameters
        ----------
        ciphertext : str
            The encrypted string

        Returns
        -------
        str
            Original plaintext

        Raises
        ------
        cryptography.fernet.InvalidToken
            If decryption fails (wrong key or corrupted data)
        """
        return self._fernet.decrypt(ciphertext.encode()).decode()


# Singleton instance
encryption_service = EncryptionService()
