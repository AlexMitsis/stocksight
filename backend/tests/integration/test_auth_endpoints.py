"""
Integration tests for authentication endpoints.

Tests user registration, login, token refresh, and protected endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.database import User
from app.services.auth_service import auth_service


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency with test database."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    # Only create tables needed for auth tests (skip conversation_embeddings)
    from app.models.database import User, PasswordResetToken

    User.__table__.create(bind=engine, checkfirst=True)
    PasswordResetToken.__table__.create(bind=engine, checkfirst=True)

    yield

    # Clean up
    PasswordResetToken.__table__.drop(bind=engine, checkfirst=True)
    User.__table__.drop(bind=engine, checkfirst=True)


@pytest.fixture
def client(test_db):
    """Create a test client with test database."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.integration
class TestUserRegistration:
    """Test user registration flow."""

    def test_register_new_user_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "country": "US",
                "preferred_currency": "USD",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Should return tokens
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Should return user data
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["country"] == "US"
        assert data["user"]["preferred_currency"] == "USD"
        assert data["user"]["is_active"] is True

    def test_register_duplicate_email(self, client):
        """Test that duplicate email registration fails."""
        # First registration
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123",
            },
        )

        # Second registration with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass456",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_weak_password_short(self, client):
        """Test that short password is rejected."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "Short1",  # Only 6 characters
            },
        )

        assert response.status_code == 422

    def test_register_weak_password_no_uppercase(self, client):
        """Test that password without uppercase is rejected."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "lowercase123",  # No uppercase
            },
        )

        assert response.status_code == 422

    def test_register_weak_password_no_lowercase(self, client):
        """Test that password without lowercase is rejected."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "UPPERCASE123",  # No lowercase
            },
        )

        assert response.status_code == 422

    def test_register_weak_password_no_number(self, client):
        """Test that password without number is rejected."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "NoNumbersHere",  # No number
            },
        )

        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        """Test that invalid email format is rejected."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 422


@pytest.mark.integration
class TestUserLogin:
    """Test user login flow."""

    def test_login_success(self, client):
        """Test successful login."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "logintest@example.com",
                "password": "SecurePass123",
            },
        )

        # Then login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "logintest@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        """Test login with incorrect password."""
        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "CorrectPass123",
            },
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPass456",
            },
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "doesnotexist@example.com",
                "password": "SomePass123",
            },
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_inactive_user(self, client):
        """Test that inactive users cannot login."""
        # Register a user
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "inactive@example.com",
                "password": "SecurePass123",
            },
        )

        # Get user_id from registration response
        user_id = register_response.json()["user"]["id"]

        # Manually deactivate user in database
        db = next(override_get_db())
        user = db.query(User).filter(User.id == user_id).first()
        user.is_active = False
        db.commit()
        db.close()

        # Try to login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()


@pytest.mark.integration
class TestTokenRefresh:
    """Test token refresh flow."""

    def test_refresh_token_success(self, client):
        """Test successful token refresh."""
        # Register and get tokens
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "SecurePass123",
            },
        )

        refresh_token = register_response.json()["refresh_token"]

        # Refresh the token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_access_token_fails(self, client):
        """Test that access token cannot be used for refresh."""
        # Register and get tokens
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "accesstoken@example.com",
                "password": "SecurePass123",
            },
        )

        access_token = register_response.json()["access_token"]

        # Try to use access token for refresh (should fail)
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client):
        """Test that invalid refresh token is rejected."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401


@pytest.mark.integration
class TestProtectedEndpoints:
    """Test protected endpoints that require authentication."""

    def test_get_current_user_success(self, client):
        """Test getting current user info with valid token."""
        # Register and get token
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "currentuser@example.com",
                "password": "SecurePass123",
                "country": "US",
                "preferred_currency": "USD",
            },
        )

        access_token = register_response.json()["access_token"]

        # Get current user info
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == "currentuser@example.com"
        assert data["country"] == "US"
        assert data["preferred_currency"] == "USD"
        assert data["is_active"] is True

    def test_get_current_user_no_token(self, client):
        """Test that accessing protected endpoint without token fails."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401  # No Authorization header

    def test_get_current_user_invalid_token(self, client):
        """Test that accessing protected endpoint with invalid token fails."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401

    def test_chat_endpoint_requires_auth(self, client, mock_agent):
        """Test that chat endpoint requires authentication."""
        response = client.post(
            "/api/chat",
            json={
                "prompt": {"content": "test", "id": "1", "role": "user"},
                "threadId": "test",
                "responseId": "resp1",
            },
        )

        # Should fail without auth token
        assert response.status_code == 401

    def test_chat_endpoint_with_valid_token(self, client, mock_agent):
        """Test that chat endpoint works with valid authentication."""
        # Register and get token
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "chatuser@example.com",
                "password": "SecurePass123",
            },
        )

        access_token = register_response.json()["access_token"]

        # Make chat request with token
        response = client.post(
            "/api/chat",
            json={
                "prompt": {"content": "What is AAPL price?", "id": "1", "role": "user"},
                "threadId": "test",
                "responseId": "resp1",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Should succeed with valid token
        assert response.status_code == 200


@pytest.mark.integration
class TestPasswordSecurity:
    """Test password security features."""

    def test_password_is_hashed(self, client):
        """Test that passwords are hashed in database, not stored in plain text."""
        # Register a user
        password = "SecurePass123"
        client.post(
            "/api/auth/register",
            json={
                "email": "hashedpass@example.com",
                "password": password,
            },
        )

        # Check database directly
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "hashedpass@example.com").first()

        # Password should be hashed (bcrypt hash starts with $2b$)
        assert user.hashed_password.startswith("$2b$")
        # Password should NOT be stored in plain text
        assert user.hashed_password != password
        # Verify the hash is valid
        assert auth_service.verify_password(password, user.hashed_password)

        db.close()


@pytest.mark.integration
class TestForgotPassword:
    """Test forgot password / password reset request flow."""

    def test_forgot_password_existing_user(self, client):
        """Test forgot password for existing user."""
        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "forgotpass@example.com",
                "password": "OldPassword123",
            },
        )

        # Request password reset
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "forgotpass@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        # Always returns generic message (email enumeration prevention)
        assert "If the email exists" in data["message"]

    def test_forgot_password_nonexistent_user(self, client):
        """Test forgot password for non-existent user (should return same message)."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "doesnotexist@example.com"},
        )

        # Should return 200 with same message (email enumeration prevention)
        assert response.status_code == 200
        data = response.json()
        assert "If the email exists" in data["message"]

    def test_forgot_password_invalid_email(self, client):
        """Test forgot password with invalid email format."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "not-an-email"},
        )

        # Should fail validation
        assert response.status_code == 422

    def test_forgot_password_creates_token(self, client):
        """Test that forgot password creates reset token in database."""
        from app.models.database import PasswordResetToken

        # Register a user
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "tokentest@example.com",
                "password": "OldPassword123",
            },
        )
        user_id = register_response.json()["user"]["id"]

        # Request password reset
        client.post(
            "/api/auth/forgot-password",
            json={"email": "tokentest@example.com"},
        )

        # Check that token was created
        db = next(override_get_db())
        tokens = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.is_used == False
        ).all()

        assert len(tokens) == 1
        assert tokens[0].user_id == user_id
        assert tokens[0].is_used is False

        db.close()

    def test_forgot_password_invalidates_old_tokens(self, client):
        """Test that requesting new reset invalidates old tokens."""
        from app.models.database import PasswordResetToken

        # Register a user
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "invalidate@example.com",
                "password": "OldPassword123",
            },
        )
        user_id = register_response.json()["user"]["id"]

        # Request password reset twice
        client.post(
            "/api/auth/forgot-password",
            json={"email": "invalidate@example.com"},
        )
        client.post(
            "/api/auth/forgot-password",
            json={"email": "invalidate@example.com"},
        )

        # Check that only one unused token exists (old one was invalidated)
        db = next(override_get_db())
        unused_tokens = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.is_used == False
        ).all()

        assert len(unused_tokens) == 1

        db.close()


@pytest.mark.integration
class TestResetPassword:
    """Test password reset confirmation flow."""

    def test_reset_password_success(self, client):
        """Test successful password reset with valid token."""
        from app.models.database import PasswordResetToken
        from datetime import datetime, timedelta

        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "resetpass@example.com",
                "password": "OldPassword123",
            },
        )

        # Create a reset token manually
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "resetpass@example.com").first()

        raw_token, hashed_token = auth_service.generate_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset_token)
        db.commit()
        db.close()

        # Reset password
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewPassword456",
            },
        )

        assert response.status_code == 200
        assert "successful" in response.json()["message"].lower()

        # Verify can login with new password
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "resetpass@example.com",
                "password": "NewPassword456",
            },
        )
        assert login_response.status_code == 200

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid-token-12345",
                "new_password": "NewPassword456",
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_reset_password_expired_token(self, client):
        """Test password reset with expired token."""
        from app.models.database import PasswordResetToken
        from datetime import datetime, timedelta

        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "expiredtoken@example.com",
                "password": "OldPassword123",
            },
        )

        # Create an expired reset token
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "expiredtoken@example.com").first()

        raw_token, hashed_token = auth_service.generate_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
        )
        db.add(reset_token)
        db.commit()
        db.close()

        # Try to reset password
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewPassword456",
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()

    def test_reset_password_used_token(self, client):
        """Test password reset with already used token."""
        from app.models.database import PasswordResetToken
        from datetime import datetime, timedelta

        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "usedtoken@example.com",
                "password": "OldPassword123",
            },
        )

        # Create a reset token
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "usedtoken@example.com").first()

        raw_token, hashed_token = auth_service.generate_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset_token)
        db.commit()
        db.close()

        # Use token once
        client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewPassword456",
            },
        )

        # Try to use same token again
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "AnotherPassword789",
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_reset_password_weak_password(self, client):
        """Test password reset with weak password."""
        from app.models.database import PasswordResetToken
        from datetime import datetime, timedelta

        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "OldPassword123",
            },
        )

        # Create a reset token
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "weakpass@example.com").first()

        raw_token, hashed_token = auth_service.generate_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset_token)
        db.commit()
        db.close()

        # Try to reset with weak password
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "weak",  # Too short
            },
        )

        assert response.status_code == 422


@pytest.mark.integration
class TestChangePassword:
    """Test password change for authenticated users."""

    def test_change_password_success(self, client):
        """Test successful password change."""
        # Register and login
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "changepass@example.com",
                "password": "OldPassword123",
            },
        )
        access_token = register_response.json()["access_token"]

        # Change password
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123",
                "new_password": "NewPassword456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert "successful" in response.json()["message"].lower()

        # Verify can login with new password
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "changepass@example.com",
                "password": "NewPassword456",
            },
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_current_password(self, client):
        """Test password change with incorrect current password."""
        # Register and login
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "wrongcurrent@example.com",
                "password": "OldPassword123",
            },
        )
        access_token = register_response.json()["access_token"]

        # Try to change with wrong current password
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPassword999",
                "new_password": "NewPassword456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_same_password(self, client):
        """Test password change with same password as current."""
        # Register and login
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "samepass@example.com",
                "password": "OldPassword123",
            },
        )
        access_token = register_response.json()["access_token"]

        # Try to change to same password
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123",
                "new_password": "OldPassword123",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()

    def test_change_password_no_auth(self, client):
        """Test password change without authentication."""
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123",
                "new_password": "NewPassword456",
            },
        )

        assert response.status_code == 401  # No Authorization header

    def test_change_password_weak_password(self, client):
        """Test password change with weak new password."""
        # Register and login
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "weaknew@example.com",
                "password": "OldPassword123",
            },
        )
        access_token = register_response.json()["access_token"]

        # Try to change to weak password
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123",
                "new_password": "weak",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 422


@pytest.mark.integration
class TestChangeEmail:
    """Test email change for authenticated users."""

    def test_change_email_success(self, client):
        """Test successful email change."""
        # Register and login
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "oldemail@example.com",
                "password": "SecurePass123",
            },
        )
        access_token = register_response.json()["access_token"]

        # Change email
        response = client.post(
            "/api/auth/change-email",
            json={
                "new_email": "newemail@example.com",
                "password": "SecurePass123",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert "newemail@example.com" in response.json()["message"]

        # Verify can login with new email
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "newemail@example.com",
                "password": "SecurePass123",
            },
        )
        assert login_response.status_code == 200

    def test_change_email_wrong_password(self, client):
        """Test email change with incorrect password."""
        # Register and login
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "SecurePass123",
            },
        )
        access_token = register_response.json()["access_token"]

        # Try to change with wrong password
        response = client.post(
            "/api/auth/change-email",
            json={
                "new_email": "newemail@example.com",
                "password": "WrongPassword456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_email_duplicate(self, client):
        """Test email change to already existing email."""
        # Register two users
        client.post(
            "/api/auth/register",
            json={
                "email": "user1@example.com",
                "password": "SecurePass123",
            },
        )
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePass456",
            },
        )
        access_token = register_response.json()["access_token"]

        # Try to change user2's email to user1's email
        response = client.post(
            "/api/auth/change-email",
            json={
                "new_email": "user1@example.com",
                "password": "SecurePass456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 400
        assert "already in use" in response.json()["detail"].lower()

    def test_change_email_no_auth(self, client):
        """Test email change without authentication."""
        response = client.post(
            "/api/auth/change-email",
            json={
                "new_email": "newemail@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 401  # No Authorization header

    def test_change_email_invalid_format(self, client):
        """Test email change with invalid email format."""
        # Register and login
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "validuser@example.com",
                "password": "SecurePass123",
            },
        )
        access_token = register_response.json()["access_token"]

        # Try to change to invalid email
        response = client.post(
            "/api/auth/change-email",
            json={
                "new_email": "not-an-email",
                "password": "SecurePass123",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 422
