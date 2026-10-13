"""
Unit tests for authentication service.

Tests password hashing, JWT token generation, and token validation.
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt

from app.services.auth_service import AuthService, auth_service
from app.core.config import settings


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test that password hashing produces a valid bcrypt hash."""
        password = "TestPassword123"
        hashed = AuthService.hash_password(password)

        # Bcrypt hashes start with $2b$ and are 60 characters long
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60
        assert hashed != password

    def test_hash_password_different_outputs(self):
        """Test that hashing the same password twice produces different hashes (due to salt)."""
        password = "TestPassword123"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        # Different hashes due to different salts
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that correct password verification returns True."""
        password = "TestPassword123"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password verification returns False."""
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test that verifying an empty password returns False."""
        password = "TestPassword123"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password("", hashed) is False


class TestAccessToken:
    """Test access token generation and validation."""

    def test_create_access_token(self):
        """Test that access token is created with correct payload."""
        user_id = 123
        token = AuthService.create_access_token(user_id=user_id)

        # Decode token (without verification for testing)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == str(user_id)
        assert "exp" in payload

    def test_create_access_token_expiry(self):
        """Test that access token has correct expiration time."""
        user_id = 123
        token = AuthService.create_access_token(user_id=user_id)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)

        # Check expiry is approximately ACCESS_TOKEN_EXPIRE_MINUTES in the future
        expected_exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        time_diff = abs((exp_datetime - expected_exp).total_seconds())

        # Allow 5 seconds of tolerance
        assert time_diff < 5

    def test_create_access_token_custom_expiry(self):
        """Test that access token can be created with custom expiration."""
        user_id = 123
        custom_delta = timedelta(minutes=60)
        token = AuthService.create_access_token(user_id=user_id, expires_delta=custom_delta)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)

        # Check expiry is approximately 60 minutes in the future
        expected_exp = datetime.utcnow() + custom_delta
        time_diff = abs((exp_datetime - expected_exp).total_seconds())

        # Allow 5 seconds of tolerance
        assert time_diff < 5

    def test_verify_token_valid(self):
        """Test that valid token verification returns user_id."""
        user_id = 123
        token = AuthService.create_access_token(user_id=user_id)

        verified_user_id = AuthService.verify_token(token)

        assert verified_user_id == user_id

    def test_verify_token_invalid(self):
        """Test that invalid token verification returns None."""
        invalid_token = "invalid.token.here"

        verified_user_id = AuthService.verify_token(invalid_token)

        assert verified_user_id is None

    def test_verify_token_expired(self):
        """Test that expired token verification returns None."""
        user_id = 123
        # Create token that expired 1 minute ago
        expired_delta = timedelta(minutes=-1)
        token = AuthService.create_access_token(user_id=user_id, expires_delta=expired_delta)

        verified_user_id = AuthService.verify_token(token)

        assert verified_user_id is None

    def test_verify_token_tampered(self):
        """Test that tampered token verification returns None."""
        user_id = 123
        token = AuthService.create_access_token(user_id=user_id)

        # Tamper with the signature. Change its first character: the last character of a
        # base64url segment can carry unused padding bits, so changing it may not alter the bytes.
        header, payload, signature = token.split(".")
        tampered_signature = ("a" if signature[0] != "a" else "b") + signature[1:]
        tampered_token = f"{header}.{payload}.{tampered_signature}"

        verified_user_id = AuthService.verify_token(tampered_token)

        assert verified_user_id is None


class TestRefreshToken:
    """Test refresh token generation and validation."""

    def test_create_refresh_token(self):
        """Test that refresh token is created with correct payload."""
        user_id = 123
        token = AuthService.create_refresh_token(user_id=user_id)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_create_refresh_token_expiry(self):
        """Test that refresh token has correct expiration time."""
        user_id = 123
        token = AuthService.create_refresh_token(user_id=user_id)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)

        # Check expiry is approximately REFRESH_TOKEN_EXPIRE_DAYS in the future
        expected_exp = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        time_diff = abs((exp_datetime - expected_exp).total_seconds())

        # Allow 5 seconds of tolerance
        assert time_diff < 5

    def test_verify_refresh_token_valid(self):
        """Test that valid refresh token verification returns user_id."""
        user_id = 123
        token = AuthService.create_refresh_token(user_id=user_id)

        verified_user_id = AuthService.verify_refresh_token(token)

        assert verified_user_id == user_id

    def test_verify_refresh_token_access_token(self):
        """Test that verifying an access token as refresh token returns None."""
        user_id = 123
        access_token = AuthService.create_access_token(user_id=user_id)

        # Access token doesn't have type="refresh"
        verified_user_id = AuthService.verify_refresh_token(access_token)

        assert verified_user_id is None

    def test_verify_refresh_token_invalid(self):
        """Test that invalid refresh token verification returns None."""
        invalid_token = "invalid.refresh.token"

        verified_user_id = AuthService.verify_refresh_token(invalid_token)

        assert verified_user_id is None

    def test_verify_refresh_token_expired(self):
        """Test that expired refresh token verification returns None."""
        user_id = 123
        # Create a refresh token manually with expired time
        expire = datetime.utcnow() + timedelta(days=-1)
        to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
        expired_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        verified_user_id = AuthService.verify_refresh_token(expired_token)

        assert verified_user_id is None


class TestResetToken:
    """Test password reset token generation and verification."""

    def test_generate_reset_token(self):
        """Test that reset token generation produces raw and hashed tokens."""
        raw_token, hashed_token = AuthService.generate_reset_token()

        # Raw token should be URL-safe base64 string
        assert isinstance(raw_token, str)
        assert len(raw_token) > 0

        # Hashed token should be SHA-256 hex digest (64 characters)
        assert isinstance(hashed_token, str)
        assert len(hashed_token) == 64

        # Tokens should be different
        assert raw_token != hashed_token

    def test_generate_reset_token_different_outputs(self):
        """Test that generating tokens twice produces different tokens."""
        raw_token1, hashed_token1 = AuthService.generate_reset_token()
        raw_token2, hashed_token2 = AuthService.generate_reset_token()

        # Each generation should produce unique tokens
        assert raw_token1 != raw_token2
        assert hashed_token1 != hashed_token2

    def test_verify_reset_token_correct(self):
        """Test that correct token verification returns True."""
        raw_token, hashed_token = AuthService.generate_reset_token()

        assert AuthService.verify_reset_token(raw_token, hashed_token) is True

    def test_verify_reset_token_incorrect(self):
        """Test that incorrect token verification returns False."""
        raw_token1, hashed_token1 = AuthService.generate_reset_token()
        raw_token2, hashed_token2 = AuthService.generate_reset_token()

        # raw_token1 should not match hashed_token2
        assert AuthService.verify_reset_token(raw_token1, hashed_token2) is False

    def test_verify_reset_token_tampered(self):
        """Test that tampered token verification returns False."""
        raw_token, hashed_token = AuthService.generate_reset_token()

        # Tamper with raw token
        tampered_token = raw_token[:-1] + ("a" if raw_token[-1] != "a" else "b")

        assert AuthService.verify_reset_token(tampered_token, hashed_token) is False

    def test_verify_reset_token_empty(self):
        """Test that empty token verification returns False."""
        _, hashed_token = AuthService.generate_reset_token()

        assert AuthService.verify_reset_token("", hashed_token) is False


class TestAuthServiceInstance:
    """Test the global auth_service instance."""

    def test_auth_service_instance(self):
        """Test that auth_service is an instance of AuthService."""
        assert isinstance(auth_service, AuthService)

    def test_auth_service_hash_password(self):
        """Test that auth_service instance can hash passwords."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)

        assert hashed.startswith("$2b$")
        assert auth_service.verify_password(password, hashed)

    def test_auth_service_create_tokens(self):
        """Test that auth_service instance can create tokens."""
        user_id = 456
        access_token = auth_service.create_access_token(user_id=user_id)
        refresh_token = auth_service.create_refresh_token(user_id=user_id)

        assert auth_service.verify_token(access_token) == user_id
        assert auth_service.verify_refresh_token(refresh_token) == user_id

    def test_auth_service_generate_reset_token(self):
        """Test that auth_service instance can generate reset tokens."""
        raw_token, hashed_token = auth_service.generate_reset_token()

        assert len(raw_token) > 0
        assert len(hashed_token) == 64
        assert auth_service.verify_reset_token(raw_token, hashed_token)
