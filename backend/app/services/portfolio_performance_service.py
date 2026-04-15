"""
Portfolio performance service for calculating metrics and preparing chart data.
"""

from sqlalchemy.orm import Session
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import yfinance as yf
from loguru import logger

from app.models.database import Holding, PortfolioSnapshot, Transaction, Dividend
from app.services.currency_service import get_currency_service


class PortfolioPerformanceService:
    """Service for portfolio performance calculations and chart data preparation."""

    def __init__(self, db: Session):
        self.db = db
        self.currency_service = get_currency_service()

    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Fetch current prices for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to current price in USD
        """
        prices = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                history = stock.history(period="1d")
                if not history.empty:
                    prices[ticker] = float(history["Close"].iloc[-1])
                    logger.debug(f"Fetched price for {ticker}: ${prices[ticker]:.2f}")
                else:
                    logger.warning(f"No price data available for {ticker}")
                    prices[ticker] = 0.0
            except Exception as e:
                logger.error(f"Error fetching price for {ticker}: {e}")
                prices[ticker] = 0.0

        return prices

    def get_portfolio_summary(
        self, user_id: int, user_currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Calculate portfolio summary with current prices.

        Args:
            user_id: User ID
            user_currency: Currency for displaying values (default: USD)

        Returns:
            Dictionary with portfolio metrics:
            - total_value: Current portfolio value
            - total_cost_basis: Total cost basis
            - total_gain_loss: Unrealized gain/loss
            - total_return_pct: Total return percentage
            - holdings_count: Number of holdings
            - holdings: List of holdings with current data
        """
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()

        if not holdings:
            return {
                "total_value": 0.0,
                "total_cost_basis": 0.0,
                "total_gain_loss": 0.0,
                "total_return_pct": 0.0,
                "holdings_count": 0,
                "holdings": [],
                "currency": user_currency,
            }

        # Fetch current prices for all holdings
        tickers = [h.ticker for h in holdings]
        current_prices = self.get_current_prices(tickers)

        # Calculate metrics for each holding
        enriched_holdings = []
        total_value_usd = 0.0
        total_cost_basis_usd = 0.0

        for holding in holdings:
            current_price_usd = current_prices.get(holding.ticker, 0.0)
            quantity = float(holding.quantity)
            cost_basis_holding = float(holding.cost_basis)

            # Convert cost basis to USD if needed
            if holding.currency != "USD":
                cost_basis_usd = self.currency_service.convert(
                    cost_basis_holding, holding.currency, "USD"
                )
            else:
                cost_basis_usd = cost_basis_holding

            # Calculate current value
            current_value_usd = current_price_usd * quantity

            # Calculate gain/loss
            gain_loss_usd = current_value_usd - cost_basis_usd
            gain_loss_pct = (
                (gain_loss_usd / cost_basis_usd * 100) if cost_basis_usd > 0 else 0.0
            )

            # Convert to user's preferred currency
            current_price = self.currency_service.convert(
                current_price_usd, "USD", user_currency
            )
            current_value = self.currency_service.convert(
                current_value_usd, "USD", user_currency
            )
            cost_basis = self.currency_service.convert(
                cost_basis_usd, "USD", user_currency
            )
            gain_loss = self.currency_service.convert(
                gain_loss_usd, "USD", user_currency
            )

            enriched_holdings.append({
                "id": holding.id,
                "ticker": holding.ticker,
                "quantity": quantity,
                "purchase_price": cost_basis / quantity if quantity > 0 else 0.0,
                "current_price": current_price,
                "cost_basis": cost_basis,
                "current_value": current_value,
                "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct,
                "currency": user_currency,
                "purchase_date": holding.purchase_date.isoformat(),
            })

            total_value_usd += current_value_usd
            total_cost_basis_usd += cost_basis_usd

        # Convert totals to user's currency
        total_value = self.currency_service.convert(
            total_value_usd, "USD", user_currency
        )
        total_cost_basis = self.currency_service.convert(
            total_cost_basis_usd, "USD", user_currency
        )
        total_gain_loss = total_value - total_cost_basis
        total_return_pct = (
            (total_gain_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
        )

        logger.info(
            f"Portfolio summary for user {user_id}: "
            f"value={total_value:.2f} {user_currency}, "
            f"cost={total_cost_basis:.2f} {user_currency}, "
            f"return={total_return_pct:.2f}%"
        )

        return {
            "total_value": round(total_value, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "total_gain_loss": round(total_gain_loss, 2),
            "total_return_pct": round(total_return_pct, 2),
            "holdings_count": len(holdings),
            "holdings": enriched_holdings,
            "currency": user_currency,
        }

    def get_allocation_data(self, user_id: int, user_currency: str = "USD") -> List[Dict[str, Any]]:
        """
        Get portfolio allocation data for pie chart.

        Aggregates multiple holdings of the same ticker into a single allocation entry.

        Args:
            user_id: User ID
            user_currency: Currency for displaying values

        Returns:
            List of holdings with allocation percentages:
            - ticker: Stock ticker
            - value: Current value (aggregated)
            - percentage: Allocation percentage
            - currency: Display currency
        """
        summary = self.get_portfolio_summary(user_id, user_currency)
        total_value = summary["total_value"]

        if total_value == 0:
            return []

        # Aggregate holdings by ticker
        ticker_values = {}
        for holding in summary["holdings"]:
            ticker = holding["ticker"]
            if ticker in ticker_values:
                ticker_values[ticker] += holding["current_value"]
            else:
                ticker_values[ticker] = holding["current_value"]

        # Build allocations list
        allocations = []
        for ticker, value in ticker_values.items():
            allocation_pct = (value / total_value * 100) if total_value > 0 else 0
            allocations.append({
                "ticker": ticker,
                "value": value,
                "percentage": round(allocation_pct, 2),
                "currency": user_currency,
            })

        # Sort by percentage descending
        allocations.sort(key=lambda x: x["percentage"], reverse=True)

        logger.info(f"Generated allocation data for user {user_id}: {len(allocations)} unique tickers")
        return allocations

    def get_gains_losses_data(self, user_id: int, user_currency: str = "USD") -> List[Dict[str, Any]]:
        """
        Get gains/losses breakdown for chart.

        Aggregates multiple holdings of the same ticker into a single gains/losses entry.

        Args:
            user_id: User ID
            user_currency: Currency for displaying values

        Returns:
            List of holdings with gain/loss data:
            - ticker: Stock ticker
            - quantity: Total quantity (aggregated)
            - purchase_price: Weighted average purchase price
            - current_price: Current market price
            - gain_loss: Unrealized gain/loss amount (aggregated)
            - gain_loss_pct: Percentage gain/loss
            - current_value: Current value (aggregated)
            - cost_basis: Cost basis (aggregated)
            - currency: Display currency
        """
        summary = self.get_portfolio_summary(user_id, user_currency)

        # Aggregate holdings by ticker
        ticker_data = {}
        for holding in summary["holdings"]:
            ticker = holding["ticker"]
            if ticker not in ticker_data:
                ticker_data[ticker] = {
                    "ticker": ticker,
                    "quantity": 0,
                    "cost_basis": 0,
                    "current_value": 0,
                    "gain_loss": 0,
                    "current_price": holding["current_price"],  # Same for all lots of same ticker
                    "currency": user_currency,
                }

            ticker_data[ticker]["quantity"] += holding["quantity"]
            ticker_data[ticker]["cost_basis"] += holding["cost_basis"]
            ticker_data[ticker]["current_value"] += holding["current_value"]
            ticker_data[ticker]["gain_loss"] += holding["gain_loss"]

        # Calculate weighted average purchase price and gain/loss percentage
        gains_losses = []
        for ticker, data in ticker_data.items():
            weighted_avg_price = data["cost_basis"] / data["quantity"] if data["quantity"] > 0 else 0
            gain_loss_pct = (data["gain_loss"] / data["cost_basis"] * 100) if data["cost_basis"] > 0 else 0

            gains_losses.append({
                "ticker": ticker,
                "quantity": data["quantity"],
                "purchase_price": weighted_avg_price,
                "current_price": data["current_price"],
                "gain_loss": data["gain_loss"],
                "gain_loss_pct": gain_loss_pct,
                "current_value": data["current_value"],
                "cost_basis": data["cost_basis"],
                "currency": user_currency,
            })

        # Sort by absolute gain/loss descending
        gains_losses.sort(key=lambda x: abs(x["gain_loss"]), reverse=True)

        logger.info(f"Generated gains/losses data for user {user_id}: {len(gains_losses)} unique tickers")
        return gains_losses

    def get_historical_value_data(
        self, user_id: int, user_currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """
        Get historical portfolio value data for line chart.

        Args:
            user_id: User ID
            user_currency: Currency for displaying values

        Returns:
            List of snapshots with date and value:
            - date: Snapshot date
            - value: Portfolio value
            - cost_basis: Total cost basis
            - currency: Display currency

        Note: If no snapshots exist, returns current value only.
        """
        snapshots = (
            self.db.query(PortfolioSnapshot)
            .filter(PortfolioSnapshot.user_id == user_id)
            .order_by(PortfolioSnapshot.snapshot_date)
            .all()
        )

        historical_data = []

        if snapshots:
            # Use existing snapshots
            for snapshot in snapshots:
                value = float(snapshot.total_value)
                cost_basis = float(snapshot.total_cost_basis)

                # Convert to user's currency using historical exchange rate from snapshot date
                # This ensures accurate historical values when viewing in non-USD currencies
                snapshot_date = snapshot.snapshot_date
                value_converted = self.currency_service.convert_at_date(
                    value, "USD", user_currency, snapshot_date
                )
                cost_basis_converted = self.currency_service.convert_at_date(
                    cost_basis, "USD", user_currency, snapshot_date
                )

                historical_data.append({
                    "date": snapshot.snapshot_date.isoformat(),
                    "value": round(value_converted, 2),
                    "cost_basis": round(cost_basis_converted, 2),
                    "currency": user_currency,
                })
        else:
            # No snapshots yet - build timeline from purchase dates
            historical_data = self._build_timeline_from_purchases(user_id, user_currency)

        logger.info(f"Retrieved historical value data for user {user_id}: {len(historical_data)} points")
        return historical_data

    def _build_timeline_from_purchases(
        self, user_id: int, user_currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """
        Build portfolio timeline from purchase dates when no snapshots exist.

        Creates data points showing portfolio value at each purchase date using
        historical prices for stocks purchased before that date.

        Args:
            user_id: User ID
            user_currency: Currency for displaying values

        Returns:
            List of historical data points with dates and portfolio values
        """
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).order_by(Holding.purchase_date).all()

        if not holdings:
            return []

        # Get unique purchase dates
        purchase_dates = sorted(set(h.purchase_date for h in holdings))

        # Build timeline showing portfolio value at each purchase date
        timeline = []
        for purchase_date in purchase_dates:
            # Get all holdings purchased on or before this date
            holdings_at_date = [h for h in holdings if h.purchase_date <= purchase_date]

            # Calculate cost basis at this date using historical exchange rates
            # Each holding's cost basis is converted using the rate from its purchase date
            cumulative_cost_basis = 0.0
            for h in holdings_at_date:
                cost_basis_converted = self.currency_service.convert_at_date(
                    float(h.cost_basis), h.currency, user_currency, h.purchase_date
                )
                cumulative_cost_basis += cost_basis_converted

            # Calculate portfolio value using historical prices for this date
            portfolio_value_usd = 0.0
            for holding in holdings_at_date:
                try:
                    # Fetch historical price for this holding on this date
                    stock = yf.Ticker(holding.ticker)
                    # Get data around the purchase date
                    hist = stock.history(start=purchase_date, end=purchase_date + timedelta(days=5))

                    if not hist.empty:
                        # Use the first available price (should be purchase_date or close to it)
                        historical_price_usd = float(hist["Close"].iloc[0])
                        quantity = float(holding.quantity)
                        portfolio_value_usd += historical_price_usd * quantity
                    else:
                        # If no data available, use cost basis for this holding
                        # Convert using historical rate from holding's purchase date
                        cost_basis_usd = self.currency_service.convert_at_date(
                            float(holding.cost_basis), holding.currency, "USD", holding.purchase_date
                        )
                        portfolio_value_usd += cost_basis_usd
                except Exception as e:
                    logger.warning(f"Failed to fetch historical price for {holding.ticker} on {purchase_date}: {e}")
                    # Fall back to cost basis with historical rate
                    cost_basis_usd = self.currency_service.convert_at_date(
                        float(holding.cost_basis), holding.currency, "USD", holding.purchase_date
                    )
                    portfolio_value_usd += cost_basis_usd

            # Convert total value to user's currency using historical rate for this timeline point
            portfolio_value = self.currency_service.convert_at_date(
                portfolio_value_usd, "USD", user_currency, purchase_date
            )

            timeline.append({
                "date": purchase_date.isoformat(),
                "value": round(portfolio_value, 2),
                "cost_basis": round(cumulative_cost_basis, 2),
                "currency": user_currency,
            })

        # Add today's current market value as the final point
        summary = self.get_portfolio_summary(user_id, user_currency)
        today = date.today()

        # Only add today if it's different from the last purchase date
        if not timeline or timeline[-1]["date"] != today.isoformat():
            timeline.append({
                "date": today.isoformat(),
                "value": summary["total_value"],
                "cost_basis": summary["total_cost_basis"],
                "currency": user_currency,
            })
        else:
            # Update the last point with current market value
            timeline[-1]["value"] = summary["total_value"]

        logger.info(f"Built timeline from purchases for user {user_id}: {len(timeline)} points")
        return timeline

    def create_portfolio_snapshot(self, user_id: int) -> PortfolioSnapshot:
        """
        Create a portfolio snapshot for today.

        Args:
            user_id: User ID

        Returns:
            Created PortfolioSnapshot object

        Raises:
            ValueError: If snapshot for today already exists
        """
        today = date.today()

        # Check if snapshot already exists for today
        existing = (
            self.db.query(PortfolioSnapshot)
            .filter(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_date == today,
            )
            .first()
        )

        if existing:
            raise ValueError(f"Snapshot for {today} already exists")

        # Get current portfolio state
        summary = self.get_portfolio_summary(user_id, "USD")  # Store in USD

        # Build holdings JSON
        holdings_json = {}
        for holding in summary["holdings"]:
            holdings_json[holding["ticker"]] = {
                "quantity": holding["quantity"],
                "current_price": holding["current_price"],
                "cost_basis": holding["cost_basis"],
                "current_value": holding["current_value"],
            }

        # Create snapshot
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            snapshot_date=today,
            total_value=Decimal(str(summary["total_value"])),
            total_cost_basis=Decimal(str(summary["total_cost_basis"])),
            holdings_json=holdings_json,
        )

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        logger.info(
            f"Created portfolio snapshot for user {user_id} on {today}: "
            f"value=${summary['total_value']:.2f}"
        )

        return snapshot


def get_portfolio_performance_service(db: Session) -> PortfolioPerformanceService:
    """Dependency injection for portfolio performance service."""
    return PortfolioPerformanceService(db)
