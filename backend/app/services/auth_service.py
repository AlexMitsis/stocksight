"""
Authentication service for password hashing, JWT token generation, and validation.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
import bcrypt
import secrets
import hashlib

from app.core.config import settings


class AuthService:
    """Service for handling authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string
        """
        # Convert password to bytes and hash with bcrypt (cost factor 12)
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if passwords match, False otherwise
        """
        # Convert to bytes for bcrypt comparison
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    @staticmethod
    def create_access_token(
        user_id: int, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User ID to encode in the token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode = {"sub": str(user_id), "exp": expire}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_id: User ID to encode in the token

        Returns:
            Encoded JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[int]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return int(user_id)
        except JWTError:
            return None
        except ValueError:
            return None

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[int]:
        """
        Verify and decode a JWT refresh token.

        Args:
            token: JWT refresh token to verify

        Returns:
            User ID if token is valid and is a refresh token, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            if user_id is None or token_type != "refresh":
                return None

            return int(user_id)
        except JWTError:
            return None
        except ValueError:
            return None

    @staticmethod
    def generate_reset_token() -> Tuple[str, str]:
        """
        Generate a secure password reset token.

        Returns:
            Tuple of (raw_token, hashed_token):
                - raw_token: URL-safe token to send to user
                - hashed_token: Hashed version to store in database
        """
        # Generate 32-byte random token (256 bits of entropy)
        raw_token = secrets.token_urlsafe(32)

        # Hash token for storage (SHA-256)
        hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()

        return raw_token, hashed_token

    @staticmethod
    def verify_reset_token(raw_token: str, hashed_token: str) -> bool:
        """
        Verify a password reset token against its hash.

        Args:
            raw_token: The raw token from user
            hashed_token: The hashed token from database

        Returns:
            True if tokens match, False otherwise
        """
        # Hash the raw token and compare
        computed_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return secrets.compare_digest(computed_hash, hashed_token)


# Global auth service instance
auth_service = AuthService()
