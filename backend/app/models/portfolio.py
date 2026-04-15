"""
Pydantic models for portfolio and holdings API endpoints.
"""

from pydantic import BaseModel, Field, field_validator, computed_field
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Literal


class HoldingCreate(BaseModel):
    """Request model for creating a new holding.

    Note: Currency is no longer user-selectable. The user's profile preferred_currency
    is automatically used for all new holdings to ensure consistency.
    """

    ticker: str = Field(..., min_length=1, max_length=20, description="Stock ticker symbol")
    quantity: Decimal = Field(..., gt=0, description="Number of shares (supports fractional)")
    purchase_price: Decimal = Field(..., gt=0, description="Per-share purchase price")
    purchase_date: date = Field(..., description="Date of purchase")

    @field_validator('ticker')
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        """Convert ticker to uppercase."""
        return v.upper().strip()

    @field_validator('purchase_date')
    @classmethod
    def validate_purchase_date(cls, v: date) -> date:
        """Ensure purchase date is not in the future."""
        if v > date.today():
            raise ValueError('Purchase date cannot be in the future')
        return v


class HoldingUpdate(BaseModel):
    """Request model for updating an existing holding.

    Note: Currency cannot be changed per holding. It is set from user's profile currency.
    """

    quantity: Optional[Decimal] = Field(None, gt=0, description="Number of shares")
    purchase_price: Optional[Decimal] = Field(None, gt=0, description="Per-share purchase price")
    purchase_date: Optional[date] = Field(None, description="Date of purchase")

    @field_validator('purchase_date')
    @classmethod
    def validate_purchase_date(cls, v: Optional[date]) -> Optional[date]:
        """Ensure purchase date is not in the future."""
        if v and v > date.today():
            raise ValueError('Purchase date cannot be in the future')
        return v


class HoldingResponse(BaseModel):
    """Response model for a holding with calculated fields."""

    id: int
    ticker: str
    quantity: Decimal
    cost_basis: Decimal  # Total cost
    purchase_price: Decimal  # Per-share price (calculated)
    purchase_date: date
    currency: str
    current_price: Optional[Decimal] = None  # Fetched on-demand from market data
    current_value: Optional[Decimal] = None  # quantity * current_price
    unrealized_gain: Optional[Decimal] = None  # current_value - cost_basis
    unrealized_gain_pct: Optional[Decimal] = None  # (unrealized_gain / cost_basis) * 100
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CSVImportPreviewRequest(BaseModel):
    """Request model for CSV import preview."""

    csv_data: str = Field(..., description="CSV file content as string")
    column_mapping: Dict[str, str] = Field(
        default={
            "ticker": "ticker",
            "quantity": "quantity",
            "purchase_price": "purchase_price",
            "purchase_date": "purchase_date",
            "currency": "currency"
        },
        description="Mapping from CSV column names to field names"
    )


class ImportWarning(BaseModel):
    """Warning about a specific row in CSV import."""

    row: int = Field(..., description="Row number (1-indexed)")
    type: str = Field(..., description="Warning type: 'invalid_ticker', 'duplicate', 'invalid_date', etc.")
    message: str = Field(..., description="Human-readable warning message")
    ticker: Optional[str] = None


class CSVImportPreviewResponse(BaseModel):
    """Response model for CSV import preview."""

    valid_rows: List[HoldingCreate] = Field(default_factory=list, description="Valid holdings that can be imported")
    warnings: List[ImportWarning] = Field(default_factory=list, description="Warnings about problematic rows")
    duplicates: List[str] = Field(default_factory=list, description="Tickers that already exist in portfolio")
    total_rows: int = Field(..., description="Total rows in CSV (excluding header)")
    valid_count: int = Field(..., description="Number of valid rows")
    warning_count: int = Field(..., description="Number of rows with warnings")


class CSVImportConfirmRequest(BaseModel):
    """Request model to confirm and execute CSV import."""

    holdings: List[HoldingCreate] = Field(..., description="List of holdings to import")


class CSVImportConfirmResponse(BaseModel):
    """Response model after CSV import execution."""

    success: bool = Field(..., description="Whether import was successful")
    added_count: int = Field(default=0, description="Number of new holdings added")
    updated_count: int = Field(default=0, description="Number of existing holdings updated")
    errors: List[str] = Field(default_factory=list, description="Any errors that occurred")
    message: str = Field(..., description="Summary message")


# =============================================================================
# Transaction Models
# =============================================================================


class TransactionCreate(BaseModel):
    """Request model for creating a new transaction.

    Transaction types:
    - BUY: Purchase shares (quantity > 0, price > 0)
    - SELL: Sell shares (quantity > 0, price > 0)
    - DIVIDEND: Dividend income (quantity = null, price = dividend amount)
    - TRANSFER_IN: Import existing position (quantity > 0, price >= 0 if cost unknown)
    - TRANSFER_OUT: Remove position (quantity > 0)
    - ADJUSTMENT: Correction (+/- quantity, quantity != 0)
    """

    ticker: str = Field(..., min_length=1, max_length=20, description="Stock ticker symbol")
    type: Literal["BUY", "SELL", "DIVIDEND", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT"] = Field(
        ..., description="Transaction type"
    )
    quantity: Optional[Decimal] = Field(None, description="Number of shares (null for DIVIDEND, can be negative for ADJUSTMENT)")
    price: Decimal = Field(default=Decimal("0.00"), ge=0, description="Per-share price (or dividend amount for DIVIDEND)")
    fees: Decimal = Field(default=Decimal("0.00"), ge=0, description="Transaction fees")
    transaction_date: date = Field(..., description="Date of transaction")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes")
    cost_basis_known: bool = Field(default=True, description="Whether cost basis is known (for TRANSFER_IN)")

    @field_validator('ticker')
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        """Convert ticker to uppercase."""
        return v.upper().strip()

    @field_validator('transaction_date')
    @classmethod
    def validate_transaction_date(cls, v: date) -> date:
        """Ensure transaction date is not in the future."""
        if v > date.today():
            raise ValueError('Transaction date cannot be in the future')
        return v

    @field_validator('quantity')
    @classmethod
    def validate_quantity_for_type(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Validate quantity based on transaction type."""
        transaction_type = info.data.get('type')

        if transaction_type in ["BUY", "SELL", "TRANSFER_IN", "TRANSFER_OUT"]:
            if v is None or v <= 0:
                raise ValueError(f"Quantity must be positive for {transaction_type} transactions")
        elif transaction_type == "DIVIDEND":
            if v is not None:
                raise ValueError("Quantity must be null for DIVIDEND transactions")
        elif transaction_type == "ADJUSTMENT":
            if v is None or v == 0:
                raise ValueError("Quantity must be non-zero for ADJUSTMENT transactions")

        return v

    @field_validator('price')
    @classmethod
    def validate_price_for_type(cls, v: Decimal, info) -> Decimal:
        """Validate price based on transaction type."""
        transaction_type = info.data.get('type')
        cost_basis_known = info.data.get('cost_basis_known', True)

        # For TRANSFER_IN with unknown cost basis, price can be 0
        if transaction_type == "TRANSFER_IN" and not cost_basis_known:
            return v

        # For other types that require price, ensure it's positive
        if transaction_type in ["BUY", "SELL", "DIVIDEND"]:
            if v <= 0:
                raise ValueError(f"Price must be positive for {transaction_type} transactions")

        return v

    @computed_field
    @property
    def total_amount(self) -> Decimal:
        """Calculate total cash flow (quantity * price + fees)."""
        if self.quantity:
            return (abs(self.quantity) * self.price) + self.fees
        return self.price  # For dividends, price is the dividend amount


class TransactionUpdate(BaseModel):
    """Request model for updating an existing transaction."""

    quantity: Optional[Decimal] = Field(None, gt=0, description="Number of shares")
    price: Optional[Decimal] = Field(None, gt=0, description="Per-share price")
    fees: Optional[Decimal] = Field(None, ge=0, description="Transaction fees")
    transaction_date: Optional[date] = Field(None, description="Date of transaction")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes")

    @field_validator('transaction_date')
    @classmethod
    def validate_transaction_date(cls, v: Optional[date]) -> Optional[date]:
        """Ensure transaction date is not in the future."""
        if v and v > date.today():
            raise ValueError('Transaction date cannot be in the future')
        return v


class TransactionResponse(BaseModel):
    """Response model for a transaction."""

    id: int
    user_id: int
    ticker: str
    type: str  # 'BUY', 'SELL', 'DIVIDEND', 'TRANSFER_IN', 'TRANSFER_OUT', 'ADJUSTMENT'
    quantity: Optional[Decimal]
    price: Decimal
    fees: Decimal
    total_amount: Decimal
    transaction_date: date
    currency: str
    notes: Optional[str]
    cost_basis_known: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Response model for list of transactions with metadata."""

    transactions: List[TransactionResponse]
    total_count: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
