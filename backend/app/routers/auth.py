"""
Authentication endpoints for user registration, login, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.auth import (
    UserRegister,
    UserLogin,
    Token,
    TokenRefresh,
    UserResponse,
    RegisterResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    ChangeEmailRequest,
    ChangeCurrencyRequest,
    ChangeCountryRequest,
    MessageResponse,
)
from app.models.database import User, PasswordResetToken
from app.services.auth_service import auth_service
from app.services.email_service import email_service
from app.services.oauth_service import oauth_service
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        user_data: User registration data (email, password, country, currency)
        db: Database session

    Returns:
        Access token, refresh token, and user data

    Raises:
        HTTPException: If email already exists or validation fails
    """
    # Hash the password
    hashed_password = auth_service.hash_password(user_data.password)

    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        country=user_data.country,
        preferred_currency=user_data.preferred_currency,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Generate tokens
    access_token = auth_service.create_access_token(user_id=new_user.id)
    refresh_token = auth_service.create_refresh_token(user_id=new_user.id)

    # Return tokens and user data
    return RegisterResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return tokens.

    Args:
        credentials: User login credentials (email, password)
        db: Database session

    Returns:
        Access token and refresh token

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    # Verify user exists and password is correct
    if not user or not auth_service.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Generate tokens
    access_token = auth_service.create_access_token(user_id=user.id)
    refresh_token = auth_service.create_refresh_token(user_id=user.id)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """
    Refresh access token using a valid refresh token.

    Args:
        token_data: Refresh token
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    # Verify refresh token
    user_id = auth_service.verify_refresh_token(token_data.refresh_token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate new access token
    access_token = auth_service.create_access_token(user_id=user.id)

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        User information
    """
    return UserResponse.model_validate(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset email.

    Always returns 200 to prevent email enumeration attacks.

    Args:
        request: Email address for password reset
        db: Database session

    Returns:
        Generic success message
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success message (don't reveal if email exists)
    message = "If the email exists, a password reset link has been sent"

    if user:
        # Invalidate all existing reset tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,  # noqa: E712
        ).update({"is_used": True})

        # Generate reset token
        raw_token, hashed_token = auth_service.generate_reset_token()

        # Store token in database (expires in 1 hour)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset_token)
        db.commit()

        # Send email (async in background would be better)
        await email_service.send_password_reset_email(user.email, raw_token)

    return MessageResponse(message=message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using reset token.

    Args:
        request: Reset token and new password
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid, expired, or already used
    """
    # Find all non-used, non-expired tokens and verify manually
    # We check each one because tokens are hashed
    reset_tokens = db.query(PasswordResetToken).filter(
        PasswordResetToken.is_used == False,  # noqa: E712
        PasswordResetToken.expires_at > datetime.utcnow(),
    ).all()

    valid_token = None
    for token in reset_tokens:
        if auth_service.verify_reset_token(request.token, token.token):
            valid_token = token
            break

    if not valid_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get user
    user = db.query(User).filter(User.id == valid_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update password
    user.hashed_password = auth_service.hash_password(request.new_password)

    # Mark token as used
    valid_token.is_used = True
    valid_token.used_at = datetime.utcnow()

    db.commit()

    # Send confirmation email
    await email_service.send_password_changed_notification(user.email)

    return MessageResponse(message="Password reset successful. You can now login with your new password.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change password for authenticated user.

    Requires current password for verification.

    Args:
        request: Current and new password
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If current password is incorrect or new password is invalid
    """
    # Verify current password
    if not auth_service.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password",
        )

    # Check if new password is same as old
    if auth_service.verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # Update password
    current_user.hashed_password = auth_service.hash_password(request.new_password)
    db.commit()

    # Send confirmation email
    await email_service.send_password_changed_notification(current_user.email)

    return MessageResponse(message="Password changed successfully")


@router.post("/change-email", response_model=MessageResponse)
async def change_email(
    request: ChangeEmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change email address for authenticated user.

    Requires password for verification.

    Args:
        request: New email and password for confirmation
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message with updated user data

    Raises:
        HTTPException: If password is incorrect or email already exists
    """
    # Verify password
    if not auth_service.verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    # Check if email is already in use
    existing_user = db.query(User).filter(User.email == request.new_email).first()
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )

    # Store old email for notification
    old_email = current_user.email

    # Update email
    current_user.email = request.new_email
    db.commit()

    # Send notifications
    await email_service.send_email_changed_notification(old_email, request.new_email)

    return MessageResponse(message=f"Email successfully changed to {request.new_email}")


@router.post("/change-currency", response_model=MessageResponse)
async def change_currency(
    request: ChangeCurrencyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change preferred currency for authenticated user.

    Args:
        request: New preferred currency
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If currency is not supported
    """
    # Update preferred currency
    current_user.preferred_currency = request.preferred_currency
    db.commit()

    return MessageResponse(message=f"Preferred currency changed to {request.preferred_currency}")


@router.post("/change-country", response_model=MessageResponse)
async def change_country(
    request: ChangeCountryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change country for authenticated user.

    Args:
        request: New country
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    # Update country
    current_user.country = request.country
    db.commit()

    return MessageResponse(message=f"Country changed to {request.country}")


# ==================== OAuth Endpoints ====================


@router.get("/oauth/google")
async def google_oauth_login():
    """
    Initiate Google OAuth flow.

    Returns:
        Redirect URL to Google's OAuth authorization page
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )

    auth_url = oauth_service.get_google_auth_url()
    return {"auth_url": auth_url}


@router.get("/oauth/google/callback", response_model=RegisterResponse)
async def google_oauth_callback(code: str, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback.

    Args:
        code: Authorization code from Google
        db: Database session

    Returns:
        Access token, refresh token, and user data

    Raises:
        HTTPException: If OAuth flow fails
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )

    try:
        result = await oauth_service.handle_google_callback(code, db)
        return RegisterResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            user=UserResponse.model_validate(result["user"]),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth failed: {str(e)}",
        )


@router.get("/oauth/github")
async def github_oauth_login():
    """
    Initiate GitHub OAuth flow.

    Returns:
        Redirect URL to GitHub's OAuth authorization page
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured",
        )

    auth_url = oauth_service.get_github_auth_url()
    return {"auth_url": auth_url}


@router.get("/oauth/github/callback", response_model=RegisterResponse)
async def github_oauth_callback(code: str, db: Session = Depends(get_db)):
    """
    Handle GitHub OAuth callback.

    Args:
        code: Authorization code from GitHub
        db: Database session

    Returns:
        Access token, refresh token, and user data

    Raises:
        HTTPException: If OAuth flow fails
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured",
        )

    try:
        result = await oauth_service.handle_github_callback(code, db)
        return RegisterResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            user=UserResponse.model_validate(result["user"]),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth failed: {str(e)}",
        )
