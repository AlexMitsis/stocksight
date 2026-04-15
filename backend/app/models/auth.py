"""
Pydantic models for authentication requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegister(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    country: Optional[str] = Field(None, max_length=2)
    preferred_currency: str = Field(default="USD", max_length=3)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets security requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserLogin(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Response model for token endpoints."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: int  # user_id
    exp: Optional[int] = None


class UserResponse(BaseModel):
    """Response model for user data."""

    id: int
    email: str
    country: Optional[str] = None
    preferred_currency: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class TokenRefresh(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class RegisterResponse(BaseModel):
    """Response model for successful registration."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request model for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class ChangePasswordRequest(BaseModel):
    """Request model for password change (authenticated users)."""

    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class ChangeEmailRequest(BaseModel):
    """Request model for email change."""

    new_email: EmailStr
    password: str


class ChangeCurrencyRequest(BaseModel):
    """Request model for currency preference change."""

    preferred_currency: str = Field(..., min_length=3, max_length=3)

    @field_validator("preferred_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code is supported."""
        v = v.upper()
        supported = ["EUR", "GBP", "CHF", "USD"]
        if v not in supported:
            raise ValueError(f"Currency must be one of: {', '.join(supported)}")
        return v


class ChangeCountryRequest(BaseModel):
    """Request model for country change."""

    country: str = Field(..., min_length=2, max_length=100)


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
