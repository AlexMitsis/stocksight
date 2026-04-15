"""
Portfolio router for managing user stock holdings.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.database import User, Holding
from app.models.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    CSVImportPreviewRequest,
    CSVImportPreviewResponse,
    CSVImportConfirmRequest,
    CSVImportConfirmResponse,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
)
from app.services.portfolio_service import PortfolioService
from app.services.csv_import_service import CSVImportService
from app.services.portfolio_performance_service import PortfolioPerformanceService
from app.services.transaction_service import TransactionService, TransactionSyncError
from loguru import logger

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _enrich_holding_with_current_price(
    holding: Holding,
    performance_service: PortfolioPerformanceService,
    user_currency: str,
) -> HoldingResponse:
    """
    Helper function to enrich a holding with current market price data.

    Args:
        holding: Holding ORM object
        performance_service: PortfolioPerformanceService instance
        user_currency: User's preferred currency

    Returns:
        HoldingResponse with current prices populated
    """
    # Get current price for this ticker
    current_prices = performance_service.get_current_prices([holding.ticker])
    current_price_usd = current_prices.get(holding.ticker, 0.0)

    # Convert to user's currency
    currency_service = performance_service.currency_service
    current_price = currency_service.convert(current_price_usd, "USD", user_currency)

    # Calculate values
    quantity = float(holding.quantity)
    cost_basis_holding = float(holding.cost_basis)

    # Convert cost basis to user currency if needed
    if holding.currency != user_currency:
        cost_basis = currency_service.convert(cost_basis_holding, holding.currency, user_currency)
    else:
        cost_basis = cost_basis_holding

    purchase_price = cost_basis / quantity if quantity > 0 else 0
    current_value = current_price * quantity
    unrealized_gain = current_value - cost_basis
    unrealized_gain_pct = (unrealized_gain / cost_basis * 100) if cost_basis > 0 else 0

    return HoldingResponse(
        id=holding.id,
        ticker=holding.ticker,
        quantity=holding.quantity,
        cost_basis=Decimal(str(cost_basis)),
        purchase_price=Decimal(str(purchase_price)),
        purchase_date=holding.purchase_date,
        currency=user_currency,
        current_price=Decimal(str(current_price)) if current_price > 0 else None,
        current_value=Decimal(str(current_value)) if current_price > 0 else None,
        unrealized_gain=Decimal(str(unrealized_gain)) if current_price > 0 else None,
        unrealized_gain_pct=Decimal(str(unrealized_gain_pct)) if current_price > 0 else None,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
    )


@router.get("/holdings", response_model=List[HoldingResponse])
async def get_holdings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all holdings for the current user with current market prices.

    Returns list of holdings with current market values calculated.
    """
    # Use PortfolioPerformanceService to get holdings with current prices
    performance_service = PortfolioPerformanceService(db)
    user_currency = current_user.preferred_currency or "USD"

    # Get portfolio summary which includes current prices
    summary = performance_service.get_portfolio_summary(current_user.id, user_currency)

    # Convert holdings from summary to response model
    response_holdings = []
    for holding_data in summary["holdings"]:
        # Parse purchase_date from ISO string to date object
        purchase_date_str = holding_data["purchase_date"]
        purchase_date_obj = date.fromisoformat(purchase_date_str) if isinstance(purchase_date_str, str) else purchase_date_str

        response_holdings.append(
            HoldingResponse(
                id=holding_data["id"],
                ticker=holding_data["ticker"],
                quantity=Decimal(str(holding_data["quantity"])),
                cost_basis=Decimal(str(holding_data["cost_basis"])),
                purchase_price=Decimal(str(holding_data["purchase_price"])),
                purchase_date=purchase_date_obj,
                currency=user_currency,
                current_price=Decimal(str(holding_data["current_price"])) if holding_data.get("current_price") else None,
                current_value=Decimal(str(holding_data["current_value"])) if holding_data.get("current_value") else None,
                unrealized_gain=Decimal(str(holding_data["gain_loss"])) if holding_data.get("gain_loss") is not None else None,
                unrealized_gain_pct=Decimal(str(holding_data["gain_loss_pct"])) if holding_data.get("gain_loss_pct") is not None else None,
                created_at=None,  # Not included in performance service response
                updated_at=None,  # Not included in performance service response
            )
        )

    return response_holdings


@router.post("/holdings", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def create_holding_deprecated():
    """
    DEPRECATED: Direct holding creation is no longer supported.

    Holdings are now managed through transactions. Use POST /api/portfolio/transactions
    with type='TRANSFER_IN' to add positions.

    This ensures all holdings have a complete audit trail via transactions.
    """
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Direct holding creation is deprecated. Use POST /api/portfolio/transactions "
               "with type='TRANSFER_IN' to add positions. This ensures full audit trail.",
    )


@router.get("/holdings/{holding_id}", response_model=HoldingResponse)
async def get_holding(
    holding_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific holding by ID with current market price.

    Raises:
        404: If holding not found or doesn't belong to user
    """
    portfolio_service = PortfolioService(db)
    performance_service = PortfolioPerformanceService(db)
    user_currency = current_user.preferred_currency or "USD"

    holding = portfolio_service.get_holding_by_id(holding_id, current_user.id)

    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding {holding_id} not found"
        )

    return _enrich_holding_with_current_price(holding, performance_service, user_currency)


@router.put("/holdings/{holding_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def update_holding_deprecated(holding_id: int):
    """
    DEPRECATED: Direct holding updates are no longer supported.

    Holdings are now managed through transactions. Use POST /api/portfolio/transactions
    with type='ADJUSTMENT' to correct positions.

    This ensures all changes have a complete audit trail via transactions.
    """
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Direct holding updates are deprecated. Use POST /api/portfolio/transactions "
               "with type='ADJUSTMENT' to correct positions. This ensures full audit trail.",
    )


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def delete_holding_deprecated(holding_id: int):
    """
    DEPRECATED: Direct holding deletion is no longer supported.

    Holdings are now managed through transactions. Use POST /api/portfolio/transactions
    with type='TRANSFER_OUT' to remove positions.

    This ensures all changes have a complete audit trail via transactions.
    """
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Direct holding deletion is deprecated. Use POST /api/portfolio/transactions "
               "with type='TRANSFER_OUT' to remove positions. This ensures full audit trail.",
    )


@router.post("/import/preview", response_model=CSVImportPreviewResponse)
async def preview_csv_import(
    request: CSVImportPreviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Preview CSV import before execution.

    Returns validated rows, warnings, and duplicate detection.
    """
    csv_import_service = CSVImportService(db)

    try:
        preview = csv_import_service.parse_csv(
            request.csv_data, request.column_mapping, current_user.id
        )
        logger.info(
            f"CSV preview: {preview.valid_count} valid rows, "
            f"{preview.warning_count} warnings, {len(preview.duplicates)} duplicates"
        )
        return preview
    except Exception as e:
        logger.error(f"CSV preview failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse CSV: {str(e)}"
        )


@router.post("/import/confirm", response_model=CSVImportConfirmResponse)
async def confirm_csv_import(
    request: CSVImportConfirmRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Execute CSV import after user confirmation.

    Creates new holdings or adds to existing ones for duplicate tickers.
    """
    csv_import_service = CSVImportService(db)

    try:
        added_count, updated_count, errors = csv_import_service.execute_import(
            request.holdings, current_user.id
        )

        success = len(errors) == 0
        message = f"Successfully imported: {added_count} new holdings, {updated_count} updated"

        if errors:
            message += f". {len(errors)} errors occurred."

        logger.info(f"CSV import completed: {message}")

        return CSVImportConfirmResponse(
            success=success,
            added_count=added_count,
            updated_count=updated_count,
            errors=errors,
            message=message,
        )
    except Exception as e:
        logger.error(f"CSV import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


@router.get("/summary")
async def get_portfolio_summary(
    currency: str = "USD",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get portfolio summary with current prices and performance metrics.

    Query Parameters:
        currency: Display currency (EUR, GBP, CHF, USD). Default: USD

    Returns:
        - total_value: Current portfolio value
        - total_cost_basis: Total cost basis
        - total_gain_loss: Unrealized gain/loss
        - total_return_pct: Total return percentage
        - holdings_count: Number of holdings
        - holdings: List of holdings with current data
        - currency: Display currency
    """
    performance_service = PortfolioPerformanceService(db)

    try:
        summary = performance_service.get_portfolio_summary(current_user.id, currency)
        return summary
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portfolio summary",
        )


@router.get("/allocation")
async def get_allocation_data(
    currency: str = "USD",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get portfolio allocation data for pie chart.

    Query Parameters:
        currency: Display currency (EUR, GBP, CHF, USD). Default: USD

    Returns:
        List of holdings with allocation percentages:
        - ticker: Stock ticker
        - value: Current value
        - percentage: Allocation percentage
        - currency: Display currency
    """
    performance_service = PortfolioPerformanceService(db)

    try:
        allocation = performance_service.get_allocation_data(current_user.id, currency)
        return allocation
    except Exception as e:
        logger.error(f"Failed to get allocation data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve allocation data",
        )


@router.get("/gains-losses")
async def get_gains_losses_data(
    currency: str = "USD",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get gains/losses breakdown for chart.

    Query Parameters:
        currency: Display currency (EUR, GBP, CHF, USD). Default: USD

    Returns:
        List of holdings with gain/loss data:
        - ticker: Stock ticker
        - gain_loss: Unrealized gain/loss amount
        - gain_loss_pct: Percentage gain/loss
        - current_value: Current value
        - cost_basis: Cost basis
        - currency: Display currency
    """
    performance_service = PortfolioPerformanceService(db)

    try:
        gains_losses = performance_service.get_gains_losses_data(current_user.id, currency)
        return gains_losses
    except Exception as e:
        logger.error(f"Failed to get gains/losses data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve gains/losses data",
        )


@router.get("/historical-value")
async def get_historical_value_data(
    currency: str = "USD",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get historical portfolio value data for line chart.

    Query Parameters:
        currency: Display currency (EUR, GBP, CHF, USD). Default: USD

    Returns:
        List of snapshots with date and value:
        - date: Snapshot date (ISO format)
        - value: Portfolio value
        - cost_basis: Total cost basis
        - currency: Display currency

    Note: If no snapshots exist, returns current value only.
    """
    performance_service = PortfolioPerformanceService(db)

    try:
        historical = performance_service.get_historical_value_data(current_user.id, currency)
        return historical
    except Exception as e:
        logger.error(f"Failed to get historical value data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve historical value data",
        )


@router.post("/snapshot", status_code=status.HTTP_201_CREATED)
async def create_portfolio_snapshot(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a portfolio snapshot for today.

    Used for tracking historical portfolio performance over time.

    Raises:
        400: If snapshot for today already exists
    """
    performance_service = PortfolioPerformanceService(db)

    try:
        snapshot = performance_service.create_portfolio_snapshot(current_user.id)
        return {
            "id": snapshot.id,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "total_value": float(snapshot.total_value),
            "total_cost_basis": float(snapshot.total_cost_basis),
            "created_at": snapshot.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portfolio snapshot",
        )


# =============================================================================
# Transaction Endpoints
# =============================================================================


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new transaction. This is the primary way to manage holdings.

    CRITICAL: This endpoint ensures atomic consistency:
    - Transaction record is created
    - Holdings table is updated accordingly
    - If holdings update fails, transaction creation is rolled back
    - BOTH succeed or BOTH fail (no partial updates)

    Transaction Types:
    - BUY: Purchase shares (creates/updates holding)
    - SELL: Sell shares (reduces holding, validates quantity)
    - DIVIDEND: Dividend income (doesn't affect holdings quantity)
    - TRANSFER_IN: Import existing position (for legacy holdings without history)
    - TRANSFER_OUT: Remove position (e.g., transfer to another broker)
    - ADJUSTMENT: Correct holdings (positive or negative quantity)

    For TRANSFER_IN with unknown cost basis:
    - Set cost_basis_known=false
    - Price can be 0

    Args:
        transaction_data: Transaction details (ticker, type, quantity, price, etc.)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created Transaction object

    Raises:
        400: Validation error (e.g., insufficient quantity for SELL)
        500: Database error or holdings sync failure
    """
    transaction_service = TransactionService(db)

    try:
        transaction = transaction_service.create_transaction(transaction_data, current_user.id)

        logger.info(
            f"Transaction created successfully: "
            f"id={transaction.id}, user={current_user.id}, "
            f"type={transaction.type}, ticker={transaction.ticker}"
        )

        return transaction

    except TransactionSyncError as e:
        # Holdings sync failed - transaction was rolled back
        logger.error(f"Transaction sync error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except ValueError as e:
        # Validation error (e.g., insufficient quantity)
        logger.warning(f"Transaction validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Unexpected error creating transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transaction",
        )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    ticker: str = None,
    type: str = None,
    start_date: date = None,
    end_date: date = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get transaction history with optional filters.

    Query Parameters:
        ticker: Filter by ticker symbol (optional)
        type: Filter by transaction type: BUY, SELL, DIVIDEND (optional)
        start_date: Filter by start date (YYYY-MM-DD) (optional)
        end_date: Filter by end date (YYYY-MM-DD) (optional)
        limit: Maximum number of results (default: 100, max: 1000)
        offset: Pagination offset (default: 0)

    Returns:
        - transactions: List of transactions sorted by date (newest first)
        - total_count: Total number of matching transactions
        - filters_applied: Summary of applied filters
    """
    transaction_service = TransactionService(db)

    # Validate type if provided
    valid_types = ["BUY", "SELL", "DIVIDEND", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT"]
    if type and type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transaction type. Must be one of: {', '.join(valid_types)}",
        )

    # Limit max results
    if limit > 1000:
        limit = 1000

    try:
        transactions = transaction_service.get_all_transactions(
            user_id=current_user.id,
            ticker=ticker,
            transaction_type=type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        # Build filters_applied dict
        filters_applied = {}
        if ticker:
            filters_applied["ticker"] = ticker
        if type:
            filters_applied["type"] = type
        if start_date:
            filters_applied["start_date"] = start_date.isoformat()
        if end_date:
            filters_applied["end_date"] = end_date.isoformat()

        return TransactionListResponse(
            transactions=transactions,
            total_count=len(transactions),
            filters_applied=filters_applied,
        )

    except Exception as e:
        logger.error(f"Failed to get transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transactions",
        )


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific transaction by ID.

    Args:
        transaction_id: Transaction ID

    Returns:
        Transaction object

    Raises:
        404: Transaction not found
    """
    transaction_service = TransactionService(db)

    transaction = transaction_service.get_transaction_by_id(transaction_id, current_user.id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    return transaction


@router.put("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing transaction and atomically adjust holdings.

    This operation:
    - Reverses the old transaction's effect on holdings
    - Updates the transaction with new values
    - Applies the new transaction's effect on holdings
    - All in one atomic database transaction

    Args:
        transaction_id: Transaction ID
        transaction_data: Updated transaction data

    Returns:
        Updated transaction

    Raises:
        404: Transaction not found
        500: Holdings sync failure
    """
    transaction_service = TransactionService(db)

    try:
        transaction = transaction_service.update_transaction(
            transaction_id, transaction_data, current_user.id
        )
        logger.info(
            f"Transaction updated: id={transaction_id}, user={current_user.id}"
        )
        return transaction

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except TransactionSyncError as e:
        logger.error(f"Failed to sync holdings after transaction update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Unexpected error updating transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transaction",
        )


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a transaction and atomically reverse its effect on holdings.

    CRITICAL: This operation:
    - Fetches the transaction
    - Reverses its effect on holdings (BUY becomes reduction, SELL becomes addition)
    - Deletes the transaction
    - All in one atomic database transaction

    Args:
        transaction_id: Transaction ID

    Returns:
        Success message

    Raises:
        404: Transaction not found
        500: Holdings sync failure
    """
    transaction_service = TransactionService(db)

    try:
        success = transaction_service.delete_transaction(transaction_id, current_user.id)

        if success:
            logger.info(f"Transaction deleted: id={transaction_id}, user={current_user.id}")
            return {"message": f"Transaction {transaction_id} deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    except TransactionSyncError as e:
        logger.error(f"Failed to reverse holdings after transaction delete: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Failed to delete transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete transaction",
        )
