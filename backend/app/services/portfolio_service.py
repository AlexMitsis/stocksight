"""
Portfolio service for managing user stock holdings.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from typing import List, Optional
from datetime import date

from app.models.database import Holding, User
from app.models.portfolio import HoldingCreate, HoldingUpdate
from loguru import logger


class PortfolioService:
    """Service for managing portfolio holdings CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_holdings(self, user_id: int) -> List[Holding]:
        """
        Get all holdings for a user.

        Args:
            user_id: User ID

        Returns:
            List of Holding objects
        """
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()
        logger.info(f"Retrieved {len(holdings)} holdings for user {user_id}")
        return holdings

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

    def create_holding(self, holding_data: HoldingCreate, user_id: int) -> Holding:
        """
        Create a new holding.

        Each purchase is tracked separately, allowing multiple holdings for the same ticker
        with different purchase dates and prices (useful for tracking cost basis per lot).

        Currency is automatically set from the user's profile preferred_currency to ensure
        consistency across all holdings.

        Args:
            holding_data: Holding creation data
            user_id: User ID

        Returns:
            Created Holding object
        """
        # Get user's preferred currency
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        currency = user.preferred_currency or "USD"

        # Calculate cost basis
        cost_basis = holding_data.quantity * holding_data.purchase_price

        holding = Holding(
            user_id=user_id,
            ticker=holding_data.ticker.upper(),
            quantity=holding_data.quantity,
            cost_basis=cost_basis,
            purchase_date=holding_data.purchase_date,
            currency=currency,  # Auto-set from user profile
        )

        try:
            self.db.add(holding)
            self.db.commit()
            self.db.refresh(holding)
            logger.info(
                f"Created holding: user={user_id}, ticker={holding.ticker}, "
                f"quantity={holding.quantity}, cost_basis={holding.cost_basis}"
            )
            return holding
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create holding: {e}")
            raise ValueError(f"Failed to create holding for {holding_data.ticker}")

    def update_holding(
        self, holding_id: int, holding_data: HoldingUpdate, user_id: int
    ) -> Optional[Holding]:
        """
        Update an existing holding.

        Args:
            holding_id: Holding ID
            holding_data: Holding update data
            user_id: User ID

        Returns:
            Updated Holding object or None if not found
        """
        holding = self.get_holding_by_id(holding_id, user_id)
        if not holding:
            return None

        # Update fields if provided
        if holding_data.quantity is not None:
            holding.quantity = holding_data.quantity

        if holding_data.purchase_price is not None:
            # Recalculate cost_basis if price changes
            purchase_price = holding_data.purchase_price
            holding.cost_basis = holding.quantity * purchase_price

        if holding_data.purchase_date is not None:
            holding.purchase_date = holding_data.purchase_date

        # Note: Currency is not updatable per holding. It comes from user's profile.

        # If quantity changed without price, recalculate cost_basis proportionally
        if holding_data.quantity is not None and holding_data.purchase_price is None:
            # Maintain the same per-share cost basis
            old_per_share = holding.cost_basis / holding.quantity
            holding.cost_basis = holding.quantity * old_per_share

        try:
            self.db.commit()
            self.db.refresh(holding)
            logger.info(
                f"Updated holding {holding_id}: ticker={holding.ticker}, "
                f"quantity={holding.quantity}, cost_basis={holding.cost_basis}"
            )
            return holding
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update holding {holding_id}: {e}")
            raise ValueError(f"Failed to update holding")

    def delete_holding(self, holding_id: int, user_id: int) -> bool:
        """
        Delete a holding.

        Args:
            holding_id: Holding ID
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        holding = self.get_holding_by_id(holding_id, user_id)
        if not holding:
            return False

        try:
            self.db.delete(holding)
            self.db.commit()
            logger.info(f"Deleted holding {holding_id} (ticker={holding.ticker}) for user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete holding {holding_id}: {e}")
            raise ValueError(f"Failed to delete holding")

    def add_to_existing_holding(
        self, ticker: str, user_id: int, quantity: Decimal, purchase_price: Decimal
    ) -> Holding:
        """
        Add shares to an existing holding (used for CSV import with duplicates).

        Currency is automatically maintained from user's profile.

        Args:
            ticker: Stock ticker
            user_id: User ID
            quantity: Additional quantity to add
            purchase_price: Purchase price of new shares

        Returns:
            Updated Holding object
        """
        holding = self.get_holding_by_ticker(ticker, user_id)
        if not holding:
            raise ValueError(f"Holding for {ticker} does not exist")

        # Calculate new totals
        additional_cost = quantity * purchase_price
        new_quantity = holding.quantity + quantity
        new_cost_basis = holding.cost_basis + additional_cost

        holding.quantity = new_quantity
        holding.cost_basis = new_cost_basis

        # Note: Currency stays the same (from user profile)

        try:
            self.db.commit()
            self.db.refresh(holding)
            logger.info(
                f"Added to holding {ticker}: +{quantity} shares, "
                f"new total={new_quantity}, new cost_basis={new_cost_basis}"
            )
            return holding
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add to holding {ticker}: {e}")
            raise ValueError(f"Failed to add to holding")


def get_portfolio_service(db: Session) -> PortfolioService:
    """Dependency injection for portfolio service."""
    return PortfolioService(db)
