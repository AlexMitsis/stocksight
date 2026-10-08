"""
Portfolio service for read-only holding lookups.

Holdings are written exclusively by TransactionService so they always stay in sync
with the transaction log.
"""

from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import Holding
from loguru import logger


class PortfolioService:
    """Service for looking up portfolio holdings."""

    def __init__(self, db: Session):
        self.db = db

    def get_holding_by_id(self, holding_id: int, user_id: int) -> Optional[Holding]:
        """
        Get a specific holding by ID.

        Args:
            holding_id: Holding ID
            user_id: User ID (ensures user can only access their own holdings)

        Returns:
            Holding object or None if not found
        """
        holding = (
            self.db.query(Holding)
            .filter(Holding.id == holding_id, Holding.user_id == user_id)
            .first()
        )

        if holding:
            logger.info(f"Retrieved holding {holding_id} for user {user_id}")
        else:
            logger.warning(f"Holding {holding_id} not found for user {user_id}")

        return holding

    def get_holding_by_ticker(self, ticker: str, user_id: int) -> Optional[Holding]:
        """
        Get a holding by ticker symbol.

        Args:
            ticker: Stock ticker symbol
            user_id: User ID

        Returns:
            Holding object or None if not found
        """
        holding = (
            self.db.query(Holding)
            .filter(Holding.ticker == ticker.upper(), Holding.user_id == user_id)
            .first()
        )
        return holding


def get_portfolio_service(db: Session) -> PortfolioService:
    """Dependency injection for portfolio service."""
    return PortfolioService(db)
