"""
Transaction service for managing stock transactions with atomic holdings sync.

This service ensures that holdings table is ALWAYS kept in sync with transactions.
All operations use database transactions to guarantee consistency.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import date

from app.models.database import Transaction, Holding, User
from app.models.portfolio import TransactionCreate, TransactionUpdate
from loguru import logger


class TransactionSyncError(Exception):
    """Raised when holdings sync fails during transaction creation."""
    pass


class TransactionService:
    """
    Service for managing portfolio transactions with atomic holdings synchronization.

    CRITICAL: All transaction operations maintain atomicity with holdings updates.
    If holdings update fails, the entire transaction is rolled back.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_transaction(
        self,
        transaction_data: TransactionCreate,
        user_id: int
    ) -> Transaction:
        """
        Create a new transaction and atomically update holdings.

        This method uses database transactions to ensure:
        1. Transaction record is created
        2. Holdings table is updated accordingly
        3. If holdings update fails, transaction creation is rolled back
        4. BOTH succeed or BOTH fail (atomicity guaranteed)

        Args:
            transaction_data: Transaction creation data
            user_id: User ID

        Returns:
            Created Transaction object

        Raises:
            TransactionSyncError: If holdings sync fails
            ValueError: If validation fails
        """
        # Get user's preferred currency
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        currency = user.preferred_currency or "USD"

        # Calculate total amount
        if transaction_data.quantity:
            total_amount = (transaction_data.quantity * transaction_data.price) + transaction_data.fees
        else:
            # For DIVIDEND transactions
            total_amount = transaction_data.price  # Price field stores dividend amount

        # Create transaction object
        transaction = Transaction(
            user_id=user_id,
            ticker=transaction_data.ticker.upper(),
            type=transaction_data.type,
            quantity=transaction_data.quantity,
            price=transaction_data.price,
            fees=transaction_data.fees,
            total_amount=total_amount,
            transaction_date=transaction_data.transaction_date,
            currency=currency,
            notes=transaction_data.notes,
            cost_basis_known=transaction_data.cost_basis_known,
        )

        try:
            # Start atomic operation
            # =====================================================================
            # CRITICAL SECTION: Both transaction and holdings must succeed together
            # =====================================================================

            # Step 1: Add transaction to session
            self.db.add(transaction)
            self.db.flush()  # Get transaction ID without committing

            logger.info(
                f"Transaction created (pending commit): user={user_id}, "
                f"type={transaction.type}, ticker={transaction.ticker}, "
                f"quantity={transaction.quantity}, amount={total_amount}"
            )

            # Step 2: Update holdings based on transaction type
            if transaction_data.type == "BUY":
                self._update_holdings_after_buy(user_id, transaction)
            elif transaction_data.type == "SELL":
                self._update_holdings_after_sell(user_id, transaction)
            elif transaction_data.type == "DIVIDEND":
                # Dividends don't affect holdings quantity
                pass
            elif transaction_data.type == "TRANSFER_IN":
                self._update_holdings_after_transfer_in(user_id, transaction)
            elif transaction_data.type == "TRANSFER_OUT":
                self._update_holdings_after_transfer_out(user_id, transaction)
            elif transaction_data.type == "ADJUSTMENT":
                self._update_holdings_after_adjustment(user_id, transaction)

            # Step 3: Commit both transaction and holdings updates atomically
            self.db.commit()
            self.db.refresh(transaction)

            logger.info(
                f"Transaction and holdings committed successfully: "
                f"transaction_id={transaction.id}"
            )

            return transaction

        except ValueError as e:
            # Validation error (e.g., insufficient quantity for SELL) - rollback
            self.db.rollback()
            logger.warning(
                f"Validation error during transaction creation. "
                f"Transaction rolled back. Error: {e}"
            )
            raise  # Re-raise ValueError as-is (will be caught by router as 400)

        except TransactionSyncError as e:
            # Holdings sync failed - rollback everything
            self.db.rollback()
            logger.error(
                f"CRITICAL: Holdings sync failed during transaction creation. "
                f"Transaction rolled back. Error: {e}"
            )
            raise TransactionSyncError(
                f"Failed to sync holdings for {transaction_data.ticker}. "
                f"Transaction was not created. Error: {str(e)}"
            )

        except (IntegrityError, SQLAlchemyError) as e:
            # Database error - rollback everything
            self.db.rollback()
            logger.error(
                f"Database error during transaction creation. "
                f"Transaction rolled back. Error: {e}"
            )
            raise ValueError(
                f"Failed to create transaction for {transaction_data.ticker}. "
                f"Database error: {str(e)}"
            )

        except Exception as e:
            # Unexpected error - rollback everything
            self.db.rollback()
            logger.error(
                f"Unexpected error during transaction creation. "
                f"Transaction rolled back. Error: {e}"
            )
            raise TransactionSyncError(
                f"Unexpected error creating transaction: {str(e)}"
            )

    def _update_holdings_after_buy(self, user_id: int, transaction: Transaction) -> None:
        """
        Update holdings table after a BUY transaction.

        Strategy: Aggregate holdings by ticker (one row per ticker).
        If holding exists, update quantity and cost_basis.
        If not, create new holding.

        Args:
            user_id: User ID
            transaction: Transaction object (already flushed to get ID)

        Raises:
            TransactionSyncError: If holdings update fails
        """
        try:
            # Check if holding exists for this ticker
            holding = (
                self.db.query(Holding)
                .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
                .first()
            )

            if holding:
                # Update existing holding (aggregate)
                old_quantity = holding.quantity
                old_cost_basis = holding.cost_basis

                holding.quantity += transaction.quantity
                holding.cost_basis += (transaction.quantity * transaction.price) + transaction.fees
                # Keep earliest purchase_date for reference
                if transaction.transaction_date < holding.purchase_date:
                    holding.purchase_date = transaction.transaction_date

                logger.info(
                    f"Holding updated (aggregated): {transaction.ticker} "
                    f"quantity: {old_quantity} → {holding.quantity}, "
                    f"cost_basis: {old_cost_basis} → {holding.cost_basis}"
                )

            else:
                # Create new holding
                holding = Holding(
                    user_id=user_id,
                    ticker=transaction.ticker,
                    quantity=transaction.quantity,
                    cost_basis=(transaction.quantity * transaction.price) + transaction.fees,
                    purchase_date=transaction.transaction_date,
                    currency=transaction.currency,
                )
                self.db.add(holding)

                logger.info(
                    f"New holding created: {transaction.ticker} "
                    f"quantity={holding.quantity}, cost_basis={holding.cost_basis}"
                )

            # Flush to detect any errors before commit
            self.db.flush()

        except Exception as e:
            logger.error(f"Holdings update after BUY failed: {e}")
            raise TransactionSyncError(f"Failed to update holdings after BUY: {str(e)}")

    def _update_holdings_after_sell(self, user_id: int, transaction: Transaction) -> None:
        """
        Update holdings table after a SELL transaction.

        Strategy:
        1. Validate sufficient quantity exists
        2. Calculate cost basis of sold shares (FIFO)
        3. Reduce holding quantity and cost_basis
        4. Delete holding if quantity becomes 0

        Args:
            user_id: User ID
            transaction: Transaction object (already flushed to get ID)

        Raises:
            ValueError: If validation fails (no holding, insufficient quantity)
            TransactionSyncError: If holdings update fails
        """
        try:
            # Get current holding
            holding = (
                self.db.query(Holding)
                .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
                .first()
            )

            if not holding:
                raise ValueError(
                    f"Cannot sell {transaction.ticker} - no holding found for this ticker"
                )

            # Validate sufficient quantity
            if holding.quantity < transaction.quantity:
                raise ValueError(
                    f"Insufficient quantity for {transaction.ticker}. "
                    f"Available: {holding.quantity}, Requested: {transaction.quantity}"
                )

            # Calculate cost basis of sold shares using FIFO
            # For now, use average cost from holding (proper FIFO calculation in separate service)
            average_cost_per_share = holding.cost_basis / holding.quantity
            cost_basis_sold = average_cost_per_share * transaction.quantity

            # Update holding
            old_quantity = holding.quantity
            old_cost_basis = holding.cost_basis

            holding.quantity -= transaction.quantity
            holding.cost_basis -= cost_basis_sold

            logger.info(
                f"Holding updated after SELL: {transaction.ticker} "
                f"quantity: {old_quantity} → {holding.quantity}, "
                f"cost_basis: {old_cost_basis} → {holding.cost_basis}"
            )

            # If all shares sold, delete holding
            if holding.quantity == 0:
                self.db.delete(holding)
                logger.info(f"Holding deleted (quantity = 0): {transaction.ticker}")

            # Flush to detect any errors before commit
            self.db.flush()

        except ValueError:
            # Re-raise validation errors (no holding, insufficient quantity)
            raise

        except TransactionSyncError:
            # Re-raise sync errors
            raise

        except Exception as e:
            logger.error(f"Holdings update after SELL failed: {e}")
            raise TransactionSyncError(f"Failed to update holdings after SELL: {str(e)}")

    def _update_holdings_after_transfer_in(self, user_id: int, transaction: Transaction) -> None:
        """
        Update holdings table after a TRANSFER_IN transaction.

        TRANSFER_IN is used for importing existing positions where the user
        may not have full transaction history. Similar to BUY but handles
        unknown cost basis.

        Args:
            user_id: User ID
            transaction: Transaction object (already flushed to get ID)

        Raises:
            TransactionSyncError: If holdings update fails
        """
        try:
            holding = (
                self.db.query(Holding)
                .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
                .first()
            )

            # Calculate cost basis (0 if unknown)
            cost_basis_to_add = (transaction.quantity * transaction.price) + transaction.fees

            if holding:
                # Update existing holding
                old_quantity = holding.quantity
                old_cost_basis = holding.cost_basis

                holding.quantity += transaction.quantity
                holding.cost_basis += cost_basis_to_add
                # Keep earliest purchase_date
                if transaction.transaction_date < holding.purchase_date:
                    holding.purchase_date = transaction.transaction_date

                logger.info(
                    f"Holding updated (TRANSFER_IN): {transaction.ticker} "
                    f"quantity: {old_quantity} → {holding.quantity}, "
                    f"cost_basis: {old_cost_basis} → {holding.cost_basis}"
                )
            else:
                # Create new holding
                holding = Holding(
                    user_id=user_id,
                    ticker=transaction.ticker,
                    quantity=transaction.quantity,
                    cost_basis=cost_basis_to_add,
                    purchase_date=transaction.transaction_date,
                    currency=transaction.currency,
                )
                self.db.add(holding)

                logger.info(
                    f"New holding created (TRANSFER_IN): {transaction.ticker} "
                    f"quantity={holding.quantity}, cost_basis={holding.cost_basis}"
                )

            self.db.flush()

        except Exception as e:
            logger.error(f"Holdings update after TRANSFER_IN failed: {e}")
            raise TransactionSyncError(f"Failed to update holdings after TRANSFER_IN: {str(e)}")

    def _update_holdings_after_transfer_out(self, user_id: int, transaction: Transaction) -> None:
        """
        Update holdings table after a TRANSFER_OUT transaction.

        TRANSFER_OUT removes shares from holdings (e.g., transferring to another broker).
        Similar to SELL but represents a transfer rather than a sale.

        Args:
            user_id: User ID
            transaction: Transaction object (already flushed to get ID)

        Raises:
            ValueError: If validation fails (no holding, insufficient quantity)
            TransactionSyncError: If holdings update fails
        """
        try:
            holding = (
                self.db.query(Holding)
                .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
                .first()
            )

            if not holding:
                raise ValueError(
                    f"Cannot transfer out {transaction.ticker} - no holding found"
                )

            if holding.quantity < transaction.quantity:
                raise ValueError(
                    f"Insufficient quantity for {transaction.ticker}. "
                    f"Available: {holding.quantity}, Requested: {transaction.quantity}"
                )

            # Use average cost for cost basis reduction
            average_cost_per_share = holding.cost_basis / holding.quantity
            cost_basis_reduction = average_cost_per_share * transaction.quantity

            old_quantity = holding.quantity
            old_cost_basis = holding.cost_basis

            holding.quantity -= transaction.quantity
            holding.cost_basis -= cost_basis_reduction

            logger.info(
                f"Holding updated (TRANSFER_OUT): {transaction.ticker} "
                f"quantity: {old_quantity} → {holding.quantity}, "
                f"cost_basis: {old_cost_basis} → {holding.cost_basis}"
            )

            if holding.quantity == 0:
                self.db.delete(holding)
                logger.info(f"Holding deleted (TRANSFER_OUT, quantity = 0): {transaction.ticker}")

            self.db.flush()

        except ValueError:
            raise

        except Exception as e:
            logger.error(f"Holdings update after TRANSFER_OUT failed: {e}")
            raise TransactionSyncError(f"Failed to update holdings after TRANSFER_OUT: {str(e)}")

    def _update_holdings_after_adjustment(self, user_id: int, transaction: Transaction) -> None:
        """
        Update holdings table after an ADJUSTMENT transaction.

        ADJUSTMENT is used for corrections. Quantity can be positive (add shares)
        or negative (remove shares). Cost basis is adjusted proportionally.

        Args:
            user_id: User ID
            transaction: Transaction object (already flushed to get ID)

        Raises:
            ValueError: If validation fails
            TransactionSyncError: If holdings update fails
        """
        try:
            holding = (
                self.db.query(Holding)
                .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
                .first()
            )

            adjustment_quantity = transaction.quantity  # Can be positive or negative

            if adjustment_quantity > 0:
                # Adding shares
                cost_basis_to_add = (adjustment_quantity * transaction.price) + transaction.fees

                if holding:
                    holding.quantity += adjustment_quantity
                    holding.cost_basis += cost_basis_to_add
                else:
                    # Create new holding for positive adjustment
                    holding = Holding(
                        user_id=user_id,
                        ticker=transaction.ticker,
                        quantity=adjustment_quantity,
                        cost_basis=cost_basis_to_add,
                        purchase_date=transaction.transaction_date,
                        currency=transaction.currency,
                    )
                    self.db.add(holding)

                logger.info(
                    f"Holding adjusted (positive): {transaction.ticker} "
                    f"added {adjustment_quantity} shares"
                )

            else:
                # Removing shares (adjustment_quantity is negative)
                if not holding:
                    raise ValueError(
                        f"Cannot adjust {transaction.ticker} - no holding found"
                    )

                removal_quantity = abs(adjustment_quantity)

                if holding.quantity < removal_quantity:
                    raise ValueError(
                        f"Insufficient quantity for adjustment on {transaction.ticker}. "
                        f"Available: {holding.quantity}, Adjustment: -{removal_quantity}"
                    )

                # Use average cost for cost basis reduction
                average_cost_per_share = holding.cost_basis / holding.quantity
                cost_basis_reduction = average_cost_per_share * removal_quantity

                holding.quantity -= removal_quantity
                holding.cost_basis -= cost_basis_reduction

                logger.info(
                    f"Holding adjusted (negative): {transaction.ticker} "
                    f"removed {removal_quantity} shares"
                )

                if holding.quantity == 0:
                    self.db.delete(holding)
                    logger.info(f"Holding deleted (ADJUSTMENT, quantity = 0): {transaction.ticker}")

            self.db.flush()

        except ValueError:
            raise

        except Exception as e:
            logger.error(f"Holdings update after ADJUSTMENT failed: {e}")
            raise TransactionSyncError(f"Failed to update holdings after ADJUSTMENT: {str(e)}")

    def get_all_transactions(
        self,
        user_id: int,
        ticker: Optional[str] = None,
        transaction_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        Get transactions with optional filters.

        Args:
            user_id: User ID
            ticker: Filter by ticker symbol (optional)
            transaction_type: Filter by type (BUY, SELL, DIVIDEND) (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of Transaction objects sorted by date (newest first)
        """
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)

        if ticker:
            query = query.filter(Transaction.ticker == ticker.upper())

        if transaction_type:
            query = query.filter(Transaction.type == transaction_type)

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)

        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        transactions = (
            query.order_by(Transaction.transaction_date.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        logger.info(f"Retrieved {len(transactions)} transactions for user {user_id}")
        return transactions

    def get_transaction_by_id(self, transaction_id: int, user_id: int) -> Optional[Transaction]:
        """
        Get a specific transaction by ID.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (ensures user can only access their own transactions)

        Returns:
            Transaction object or None if not found
        """
        transaction = (
            self.db.query(Transaction)
            .filter(Transaction.id == transaction_id, Transaction.user_id == user_id)
            .first()
        )

        if transaction:
            logger.info(f"Retrieved transaction {transaction_id} for user {user_id}")
        else:
            logger.warning(f"Transaction {transaction_id} not found for user {user_id}")

        return transaction

    def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """
        Delete a transaction and atomically reverse its effect on holdings.

        CRITICAL: This operation:
        1. Fetches the transaction
        2. Reverses its effect on holdings (BUY becomes SELL, SELL becomes BUY)
        3. Deletes the transaction
        4. All in one atomic database transaction

        Args:
            transaction_id: Transaction ID
            user_id: User ID

        Returns:
            True if deleted successfully

        Raises:
            TransactionSyncError: If holdings sync fails
            ValueError: If transaction not found
        """
        transaction = self.get_transaction_by_id(transaction_id, user_id)
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        try:
            # Start atomic operation
            # =====================================================================
            # CRITICAL SECTION: Both deletion and holdings reversal must succeed
            # =====================================================================

            # Reverse the transaction's effect on holdings
            if transaction.type == "BUY":
                self._reverse_buy_transaction(user_id, transaction)
            elif transaction.type == "SELL":
                self._reverse_sell_transaction(user_id, transaction)
            elif transaction.type == "TRANSFER_IN":
                self._reverse_transfer_in_transaction(user_id, transaction)
            elif transaction.type == "TRANSFER_OUT":
                self._reverse_transfer_out_transaction(user_id, transaction)
            elif transaction.type == "ADJUSTMENT":
                self._reverse_adjustment_transaction(user_id, transaction)
            # DIVIDEND has no holdings effect to reverse

            # Delete transaction
            self.db.delete(transaction)

            # Commit atomically
            self.db.commit()

            logger.info(
                f"Transaction deleted and holdings reversed: "
                f"transaction_id={transaction_id}, type={transaction.type}, "
                f"ticker={transaction.ticker}"
            )

            return True

        except TransactionSyncError:
            self.db.rollback()
            raise

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete transaction {transaction_id}: {e}")
            raise TransactionSyncError(f"Failed to delete transaction: {str(e)}")

    def _reverse_buy_transaction(self, user_id: int, transaction: Transaction) -> None:
        """Reverse the effect of a BUY transaction on holdings."""
        holding = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
            .first()
        )

        if not holding:
            raise TransactionSyncError(
                f"Cannot reverse BUY - no holding found for {transaction.ticker}"
            )

        # Reduce quantity and cost_basis
        holding.quantity -= transaction.quantity
        holding.cost_basis -= (transaction.quantity * transaction.price) + transaction.fees

        if holding.quantity <= 0:
            self.db.delete(holding)
            logger.info(f"Holding deleted after reversing BUY: {transaction.ticker}")
        else:
            self.db.flush()

    def _reverse_sell_transaction(self, user_id: int, transaction: Transaction) -> None:
        """Reverse the effect of a SELL transaction on holdings."""
        from sqlalchemy import func

        holding = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
            .first()
        )

        # Calculate cost basis to add back using average cost from BUY transactions
        # This is more accurate than using the sell price
        avg_cost_result = (
            self.db.query(
                func.sum(Transaction.quantity * Transaction.price) / func.sum(Transaction.quantity)
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.ticker == transaction.ticker,
                Transaction.type == "BUY",
            )
            .scalar()
        )

        # Use average cost from BUYs, or fall back to current holding's average if no BUYs found
        if avg_cost_result:
            average_cost_per_share = Decimal(str(avg_cost_result))
        elif holding and holding.quantity > 0:
            average_cost_per_share = holding.cost_basis / holding.quantity
        else:
            # Last resort: use the sell price (not ideal but prevents division by zero)
            average_cost_per_share = transaction.price
            logger.warning(
                f"Could not determine average cost for {transaction.ticker}, "
                f"using sell price as fallback"
            )

        cost_basis_to_add = average_cost_per_share * transaction.quantity

        logger.info(
            f"Reversing SELL: {transaction.ticker}, quantity={transaction.quantity}, "
            f"avg_cost={average_cost_per_share}, cost_basis_to_add={cost_basis_to_add}"
        )

        if holding:
            # Add back to existing holding
            holding.quantity += transaction.quantity
            holding.cost_basis += cost_basis_to_add
        else:
            # Recreate holding
            holding = Holding(
                user_id=user_id,
                ticker=transaction.ticker,
                quantity=transaction.quantity,
                cost_basis=cost_basis_to_add,
                purchase_date=transaction.transaction_date,
                currency=transaction.currency,
            )
            self.db.add(holding)

        self.db.flush()

    def _reverse_transfer_in_transaction(self, user_id: int, transaction: Transaction) -> None:
        """Reverse the effect of a TRANSFER_IN transaction on holdings."""
        holding = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
            .first()
        )

        if not holding:
            raise TransactionSyncError(
                f"Cannot reverse TRANSFER_IN - no holding found for {transaction.ticker}"
            )

        cost_basis_to_remove = (transaction.quantity * transaction.price) + transaction.fees

        holding.quantity -= transaction.quantity
        holding.cost_basis -= cost_basis_to_remove

        if holding.quantity <= 0:
            self.db.delete(holding)
            logger.info(f"Holding deleted after reversing TRANSFER_IN: {transaction.ticker}")
        else:
            self.db.flush()

    def _reverse_transfer_out_transaction(self, user_id: int, transaction: Transaction) -> None:
        """Reverse the effect of a TRANSFER_OUT transaction on holdings."""
        from sqlalchemy import func

        holding = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
            .first()
        )

        # Calculate cost basis using average from buy/transfer_in transactions
        avg_cost_result = (
            self.db.query(
                func.sum(Transaction.quantity * Transaction.price) / func.sum(Transaction.quantity)
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.ticker == transaction.ticker,
                Transaction.type.in_(["BUY", "TRANSFER_IN"]),
            )
            .scalar()
        )

        if avg_cost_result:
            average_cost_per_share = Decimal(str(avg_cost_result))
        elif holding and holding.quantity > 0:
            average_cost_per_share = holding.cost_basis / holding.quantity
        else:
            average_cost_per_share = transaction.price or Decimal("0")
            logger.warning(
                f"Could not determine average cost for {transaction.ticker} reversal, "
                f"using fallback"
            )

        cost_basis_to_add = average_cost_per_share * transaction.quantity

        if holding:
            holding.quantity += transaction.quantity
            holding.cost_basis += cost_basis_to_add
        else:
            holding = Holding(
                user_id=user_id,
                ticker=transaction.ticker,
                quantity=transaction.quantity,
                cost_basis=cost_basis_to_add,
                purchase_date=transaction.transaction_date,
                currency=transaction.currency,
            )
            self.db.add(holding)

        self.db.flush()

    def _reverse_adjustment_transaction(self, user_id: int, transaction: Transaction) -> None:
        """Reverse the effect of an ADJUSTMENT transaction on holdings."""
        holding = (
            self.db.query(Holding)
            .filter(Holding.user_id == user_id, Holding.ticker == transaction.ticker)
            .first()
        )

        adjustment_quantity = transaction.quantity

        if adjustment_quantity > 0:
            # Original was positive adjustment (added shares), so remove them
            if not holding:
                raise TransactionSyncError(
                    f"Cannot reverse ADJUSTMENT - no holding found for {transaction.ticker}"
                )

            cost_basis_to_remove = (adjustment_quantity * transaction.price) + transaction.fees
            holding.quantity -= adjustment_quantity
            holding.cost_basis -= cost_basis_to_remove

            if holding.quantity <= 0:
                self.db.delete(holding)
                logger.info(f"Holding deleted after reversing positive ADJUSTMENT: {transaction.ticker}")

        else:
            # Original was negative adjustment (removed shares), so add them back
            removal_quantity = abs(adjustment_quantity)

            # Calculate average cost for re-adding
            if holding and holding.quantity > 0:
                average_cost_per_share = holding.cost_basis / holding.quantity
            else:
                average_cost_per_share = transaction.price or Decimal("0")

            cost_basis_to_add = average_cost_per_share * removal_quantity

            if holding:
                holding.quantity += removal_quantity
                holding.cost_basis += cost_basis_to_add
            else:
                holding = Holding(
                    user_id=user_id,
                    ticker=transaction.ticker,
                    quantity=removal_quantity,
                    cost_basis=cost_basis_to_add,
                    purchase_date=transaction.transaction_date,
                    currency=transaction.currency,
                )
                self.db.add(holding)

        self.db.flush()

    def update_transaction(
        self,
        transaction_id: int,
        transaction_data: TransactionUpdate,
        user_id: int
    ) -> Transaction:
        """
        Update a transaction and atomically adjust holdings.

        This method:
        1. Reverses the old transaction's effect on holdings
        2. Updates the transaction with new values
        3. Applies the new transaction's effect on holdings
        4. All in one atomic database transaction

        Args:
            transaction_id: Transaction ID to update
            transaction_data: New transaction data
            user_id: User ID

        Returns:
            Updated Transaction object

        Raises:
            TransactionSyncError: If holdings sync fails
            ValueError: If transaction not found or validation fails
        """
        transaction = self.get_transaction_by_id(transaction_id, user_id)
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        try:
            # Step 1: Reverse the old transaction's effect on holdings
            if transaction.type == "BUY":
                self._reverse_buy_transaction(user_id, transaction)
            elif transaction.type == "SELL":
                self._reverse_sell_transaction(user_id, transaction)
            elif transaction.type == "TRANSFER_IN":
                self._reverse_transfer_in_transaction(user_id, transaction)
            elif transaction.type == "TRANSFER_OUT":
                self._reverse_transfer_out_transaction(user_id, transaction)
            elif transaction.type == "ADJUSTMENT":
                self._reverse_adjustment_transaction(user_id, transaction)
            # DIVIDEND has no holdings effect

            # Step 2: Update transaction fields
            if transaction_data.quantity is not None:
                transaction.quantity = transaction_data.quantity
            if transaction_data.price is not None:
                transaction.price = transaction_data.price
            if transaction_data.fees is not None:
                transaction.fees = transaction_data.fees
            if transaction_data.transaction_date is not None:
                transaction.transaction_date = transaction_data.transaction_date
            if transaction_data.notes is not None:
                transaction.notes = transaction_data.notes

            # Recalculate total amount
            if transaction.quantity:
                transaction.total_amount = (transaction.quantity * transaction.price) + transaction.fees
            else:
                transaction.total_amount = transaction.price

            # Step 3: Apply the new transaction's effect on holdings
            if transaction.type == "BUY":
                self._update_holdings_after_buy(user_id, transaction)
            elif transaction.type == "SELL":
                self._update_holdings_after_sell(user_id, transaction)
            elif transaction.type == "TRANSFER_IN":
                self._update_holdings_after_transfer_in(user_id, transaction)
            elif transaction.type == "TRANSFER_OUT":
                self._update_holdings_after_transfer_out(user_id, transaction)
            elif transaction.type == "ADJUSTMENT":
                self._update_holdings_after_adjustment(user_id, transaction)
            # DIVIDEND has no holdings effect

            # Step 4: Commit atomically
            self.db.commit()
            self.db.refresh(transaction)

            logger.info(
                f"Transaction updated: id={transaction_id}, "
                f"type={transaction.type}, ticker={transaction.ticker}"
            )

            return transaction

        except TransactionSyncError:
            self.db.rollback()
            raise

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update transaction {transaction_id}: {e}")
            raise TransactionSyncError(f"Failed to update transaction: {str(e)}")


def get_transaction_service(db: Session) -> TransactionService:
    """Dependency injection for transaction service."""
    return TransactionService(db)
