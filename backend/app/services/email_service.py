"""
Email service for sending transactional emails.

For development: Logs emails to console
For production: Use SendGrid, AWS SES, or similar service
"""

from loguru import logger
from app.core.config import settings


class EmailService:
    """Service for sending emails."""

    @staticmethod
    async def send_password_reset_email(email: str, reset_token: str) -> bool:
        """
        Send password reset email to user.

        Args:
            email: User's email address
            reset_token: Password reset token

        Returns:
            True if email sent successfully, False otherwise
        """
        # Construct reset link
        # In production, use actual frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        # For development: Log to console
        # TODO: In production, use SendGrid/AWS SES
        logger.info("=" * 80)
        logger.info("PASSWORD RESET EMAIL")
        logger.info("=" * 80)
        logger.info(f"To: {email}")
        logger.info(f"Subject: Reset Your Password")
        logger.info("")
        logger.info("Email Body:")
        logger.info("-" * 80)
        logger.info("Hi there,")
        logger.info("")
        logger.info("You requested to reset your password. Click the link below to reset it:")
        logger.info("")
        logger.info(f"  {reset_link}")
        logger.info("")
        logger.info("This link expires in 1 hour.")
        logger.info("")
        logger.info("If you didn't request this, please ignore this email.")
        logger.info("")
        logger.info("Best regards,")
        logger.info("Stock Analysis Team")
        logger.info("-" * 80)
        logger.info("=" * 80)

        return True

    @staticmethod
    async def send_password_changed_notification(email: str) -> bool:
        """
        Send notification email when password is changed.

        Args:
            email: User's email address

        Returns:
            True if email sent successfully, False otherwise
        """
        logger.info("=" * 80)
        logger.info("PASSWORD CHANGED NOTIFICATION")
        logger.info("=" * 80)
        logger.info(f"To: {email}")
        logger.info(f"Subject: Your Password Was Changed")
        logger.info("")
        logger.info("Email Body:")
        logger.info("-" * 80)
        logger.info("Hi there,")
        logger.info("")
        logger.info("Your password was successfully changed.")
        logger.info("")
        logger.info("If you didn't make this change, please contact support immediately.")
        logger.info("")
        logger.info("Best regards,")
        logger.info("Stock Analysis Team")
        logger.info("-" * 80)
        logger.info("=" * 80)

        return True

    @staticmethod
    async def send_email_changed_notification(old_email: str, new_email: str) -> bool:
        """
        Send notification when email is changed.

        Args:
            old_email: Previous email address
            new_email: New email address

        Returns:
            True if email sent successfully, False otherwise
        """
        # Send to old email
        logger.info("=" * 80)
        logger.info("EMAIL CHANGED NOTIFICATION (Old Address)")
        logger.info("=" * 80)
        logger.info(f"To: {old_email}")
        logger.info(f"Subject: Your Email Address Was Changed")
        logger.info("")
        logger.info("Email Body:")
        logger.info("-" * 80)
        logger.info("Hi there,")
        logger.info("")
        logger.info(f"Your email address was changed to: {new_email}")
        logger.info("")
        logger.info("If you didn't make this change, please contact support immediately.")
        logger.info("")
        logger.info("Best regards,")
        logger.info("Stock Analysis Team")
        logger.info("-" * 80)
        logger.info("=" * 80)

        # Send to new email
        logger.info("=" * 80)
        logger.info("EMAIL CHANGED NOTIFICATION (New Address)")
        logger.info("=" * 80)
        logger.info(f"To: {new_email}")
        logger.info(f"Subject: Welcome to Your New Email Address")
        logger.info("")
        logger.info("Email Body:")
        logger.info("-" * 80)
        logger.info("Hi there,")
        logger.info("")
        logger.info("Your email address for Stock Analysis was successfully changed.")
        logger.info("")
        logger.info("You can now use this email to login.")
        logger.info("")
        logger.info("Best regards,")
        logger.info("Stock Analysis Team")
        logger.info("-" * 80)
        logger.info("=" * 80)

        return True


# Global email service instance
email_service = EmailService()
