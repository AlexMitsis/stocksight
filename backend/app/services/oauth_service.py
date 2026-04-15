"""
OAuth authentication service for Google and GitHub providers.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
import httpx

from app.core.config import settings
from app.models.database import User, OAuthAccount
from app.services.auth_service import auth_service


class OAuthService:
    """Service for OAuth authentication with Google and GitHub."""

    # OAuth Provider URLs
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USERINFO_URL = "https://api.github.com/user"
    GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

    @staticmethod
    def get_google_auth_url() -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{OAuthService.GOOGLE_AUTH_URL}?{query_string}"

    @staticmethod
    def get_github_auth_url() -> str:
        """Generate GitHub OAuth authorization URL."""
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": "user:email",
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{OAuthService.GITHUB_AUTH_URL}?{query_string}"

    @staticmethod
    async def handle_google_callback(code: str, db: Session) -> Dict[str, Any]:
        """
        Handle Google OAuth callback.

        Args:
            code: Authorization code from Google
            db: Database session

        Returns:
            Dict with access_token, refresh_token, and user data
        """
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                OAuthService.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            tokens = token_response.json()

            # Get user info
            userinfo_response = await client.get(
                OAuthService.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

        # Find or create user
        email = userinfo["email"]
        google_user_id = userinfo["id"]

        user = await OAuthService._find_or_create_user(
            db=db,
            provider="google",
            provider_user_id=google_user_id,
            email=email,
            provider_access_token=tokens.get("access_token"),
            provider_refresh_token=tokens.get("refresh_token"),
        )

        # Generate our JWT tokens
        access_token = auth_service.create_access_token(user_id=user.id)
        refresh_token = auth_service.create_refresh_token(user_id=user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user,
        }

    @staticmethod
    async def handle_github_callback(code: str, db: Session) -> Dict[str, Any]:
        """
        Handle GitHub OAuth callback.

        Args:
            code: Authorization code from GitHub
            db: Database session

        Returns:
            Dict with access_token, refresh_token, and user data
        """
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                OAuthService.GITHUB_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "redirect_uri": settings.GITHUB_REDIRECT_URI,
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            tokens = token_response.json()
            access_token = tokens["access_token"]

            # Get user info
            userinfo_response = await client.get(
                OAuthService.GITHUB_USERINFO_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

            # Get primary email (GitHub doesn't always include email in user info)
            email = userinfo.get("email")
            if not email:
                emails_response = await client.get(
                    OAuthService.GITHUB_EMAILS_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
                emails_response.raise_for_status()
                emails = emails_response.json()
                primary_email = next((e for e in emails if e["primary"]), None)
                if primary_email:
                    email = primary_email["email"]

        if not email:
            raise ValueError("Could not retrieve email from GitHub")

        github_user_id = str(userinfo["id"])

        user = await OAuthService._find_or_create_user(
            db=db,
            provider="github",
            provider_user_id=github_user_id,
            email=email,
            provider_access_token=access_token,
            provider_refresh_token=None,  # GitHub doesn't provide refresh tokens
        )

        # Generate our JWT tokens
        our_access_token = auth_service.create_access_token(user_id=user.id)
        our_refresh_token = auth_service.create_refresh_token(user_id=user.id)

        return {
            "access_token": our_access_token,
            "refresh_token": our_refresh_token,
            "token_type": "bearer",
            "user": user,
        }

    @staticmethod
    async def _find_or_create_user(
        db: Session,
        provider: str,
        provider_user_id: str,
        email: str,
        provider_access_token: Optional[str] = None,
        provider_refresh_token: Optional[str] = None,
    ) -> User:
        """
        Find existing user by OAuth account or create new user.

        Args:
            db: Database session
            provider: OAuth provider name ('google' or 'github')
            provider_user_id: User ID from provider
            email: User email
            provider_access_token: Access token from provider
            provider_refresh_token: Refresh token from provider

        Returns:
            User object
        """
        # Check if OAuth account exists
        oauth_account = (
            db.query(OAuthAccount)
            .filter(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
            .first()
        )

        if oauth_account:
            # Update tokens
            oauth_account.access_token = provider_access_token
            oauth_account.refresh_token = provider_refresh_token
            oauth_account.email = email
            db.commit()
            db.refresh(oauth_account)
            return oauth_account.user

        # Check if user exists with this email
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Create new user (OAuth users don't have password)
            # Use a random password hash as placeholder
            import secrets

            random_password = secrets.token_urlsafe(32)
            user = User(
                email=email,
                hashed_password=auth_service.hash_password(random_password),
                is_active=True,
            )
            db.add(user)
            db.flush()  # Get user.id before creating OAuth account

        # Create OAuth account linked to user
        new_oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            access_token=provider_access_token,
            refresh_token=provider_refresh_token,
        )
        db.add(new_oauth_account)
        db.commit()
        db.refresh(user)

        return user


oauth_service = OAuthService()
