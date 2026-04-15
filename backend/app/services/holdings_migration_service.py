"""
Holdings migration service for creating TRANSFER_IN transactions for orphaned holdings.

Orphaned holdings are holdings that exist in the holdings table but have no
corresponding transactions in the transactions table.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from typing import List, Tuple

from app.models.database import Holding, Transaction, User
from app.models.portfolio import TransactionCreate
from app.services.transaction_service import TransactionService
from loguru import logger


class HoldingsMigrationService:
    """
    Service for migrating orphaned holdings to transactions.

    This service runs on application startup to ensure all holdings
    have backing transactions (single source of truth).
    """

    def __init__(self, db: Session):
        self.db = db
        self.transaction_service = TransactionService(db)

    def find_orphaned_holdings(self) -> List[Tuple[Holding, Decimal]]:
        """
        Find holdings that don't have sufficient backing transactions.

        A holding is considered orphaned if the sum of its transactions
        (BUY + TRANSFER_IN - SELL - TRANSFER_OUT ± ADJUSTMENT) doesn't
        match the holding's quantity.

        Returns:
            List of (Holding, deficit) tuples where deficit is the
            quantity not covered by transactions
        """
        orphaned = []

        # Get all holdings
        holdings = self.db.query(Holding).all()

        for holding in holdings:
            # Calculate net quantity from transactions
            tx_quantity = (
                self.db.query(
                    func.coalesce(
                        func.sum(
                            func.case(
                                (Transaction.type.in_(["BUY", "TRANSFER_IN"]), Transaction.quantity),
                                (Transaction.type.in_(["SELL", "TRANSFER_OUT"]), -Transaction.quantity),
                                (Transaction.type == "ADJUSTMENT", Transaction.quantity),
                                else_=0
                            )
                        ),
                        0
                    )
                )
                .filter(
                    Transaction.user_id == holding.user_id,
                    Transaction.ticker == holding.ticker,
                )
                .scalar()
            )

            tx_quantity = Decimal(str(tx_quantity or 0))
            holding_quantity = Decimal(str(holding.quantity))

            # If there's a deficit, the holding is orphaned
            deficit = holding_quantity - tx_quantity

            if deficit > 0:
                logger.info(
                    f"Found orphaned holding: user={holding.user_id}, "
                    f"ticker={holding.ticker}, holding_qty={holding_quantity}, "
                    f"tx_qty={tx_quantity}, deficit={deficit}"
                )
                orphaned.append((holding, deficit))

        return orphaned

    def migrate_orphaned_holdings(self) -> int:
        """
        Create TRANSFER_IN transactions for all orphaned holdings.

        This ensures every holding has backing transactions.

        Returns:
            Number of TRANSFER_IN transactions created
        """
        orphaned = self.find_orphaned_holdings()

        if not orphaned:
            logger.info("No orphaned holdings found - all holdings have backing transactions")
            return 0

        migrated_count = 0

        for holding, deficit in orphaned:
            try:
                # Calculate average cost per share for the deficit
                if holding.quantity > 0 and holding.cost_basis > 0:
                    # Pro-rate the cost basis for the deficit
                    avg_cost = holding.cost_basis / holding.quantity
                else:
                    avg_cost = Decimal("0")

                # Create TRANSFER_IN transaction
                transaction_data = TransactionCreate(
                    ticker=holding.ticker,
                    type="TRANSFER_IN",
                    quantity=deficit,
                    price=avg_cost,
                    fees=Decimal("0.00"),
                    transaction_date=holding.purchase_date,
                    notes="Auto-migrated from legacy holding (no transaction history)",
                    cost_basis_known=avg_cost > 0,
                )

                # Note: We need to create transaction without triggering holdings update
                # since the holding already exists. So we create the transaction record directly.
                user = self.db.query(User).filter(User.id == holding.user_id).first()
                if not user:
                    logger.warning(f"User {holding.user_id} not found, skipping holding {holding.id}")
                    continue

                currency = user.preferred_currency or "USD"

                # Calculate total amount
                total_amount = (deficit * avg_cost)

                # Create transaction directly (bypassing holdings sync since holding exists)
                transaction = Transaction(
                    user_id=holding.user_id,
                    ticker=holding.ticker,
                    type="TRANSFER_IN",
                    quantity=deficit,
                    price=avg_cost,
                    fees=Decimal("0.00"),
                    total_amount=total_amount,
                    transaction_date=holding.purchase_date,
                    currency=currency,
                    notes="Auto-migrated from legacy holding (no transaction history)",
                    cost_basis_known=avg_cost > 0,
                )

                self.db.add(transaction)
                self.db.flush()

                logger.info(
                    f"Created TRANSFER_IN for orphaned holding: "
                    f"user={holding.user_id}, ticker={holding.ticker}, "
                    f"quantity={deficit}, price={avg_cost}"
                )

                migrated_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to migrate orphaned holding: "
                    f"user={holding.user_id}, ticker={holding.ticker}, error={e}"
                )
                # Continue with other holdings
                continue

        # Commit all migrations
        if migrated_count > 0:
            self.db.commit()
            logger.info(f"Successfully migrated {migrated_count} orphaned holdings")

        return migrated_count


def get_holdings_migration_service(db: Session) -> HoldingsMigrationService:
    """Dependency injection for holdings migration service."""
    return HoldingsMigrationService(db)
