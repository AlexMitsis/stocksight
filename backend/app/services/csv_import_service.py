"""
CSV import service for bulk portfolio imports.
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models.portfolio import (
    HoldingCreate,
    TransactionCreate,
    CSVImportPreviewResponse,
    ImportWarning,
)
from app.services.portfolio_service import PortfolioService
from app.services.transaction_service import TransactionService
from loguru import logger


class CSVImportService:
    """Service for importing portfolio holdings from CSV files."""

    SUPPORTED_DATE_FORMATS = [
        "%Y-%m-%d",  # 2024-01-15
        "%m/%d/%Y",  # 01/15/2024
        "%d/%m/%Y",  # 15/01/2024
        "%Y/%m/%d",  # 2024/01/15
        "%d-%m-%Y",  # 15-01-2024
    ]

    def __init__(self, db: Session):
        self.db = db
        self.portfolio_service = PortfolioService(db)
        self.transaction_service = TransactionService(db)

    def parse_csv(
        self, csv_data: str, column_mapping: dict, user_id: int
    ) -> CSVImportPreviewResponse:
        """
        Parse CSV data and validate rows.

        Args:
            csv_data: CSV file content as string
            column_mapping: Mapping from CSV column names to field names
            user_id: User ID (to check for duplicates)

        Returns:
            CSVImportPreviewResponse with valid rows and warnings
        """
        valid_rows: List[HoldingCreate] = []
        warnings: List[ImportWarning] = []
        duplicates: List[str] = []

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_data))
        total_rows = 0

        for row_idx, row in enumerate(reader, start=1):
            total_rows += 1

            try:
                # Map columns
                mapped_row = self._map_columns(row, column_mapping)

                # Validate and create holding object
                holding = self._validate_row(mapped_row, row_idx, warnings)

                if holding:
                    # Check for duplicates in user's existing portfolio
                    existing = self.portfolio_service.get_holding_by_ticker(
                        holding.ticker, user_id
                    )
                    if existing:
                        duplicates.append(holding.ticker)
                        warnings.append(
                            ImportWarning(
                                row=row_idx,
                                type="duplicate",
                                message=f"Ticker {holding.ticker} already exists in portfolio. "
                                f"Importing will add {holding.quantity} shares to existing {existing.quantity} shares.",
                                ticker=holding.ticker,
                            )
                        )

                    valid_rows.append(holding)

            except Exception as e:
                logger.error(f"Error parsing row {row_idx}: {e}")
                warnings.append(
                    ImportWarning(
                        row=row_idx,
                        type="parse_error",
                        message=f"Failed to parse row: {str(e)}",
                    )
                )

        return CSVImportPreviewResponse(
            valid_rows=valid_rows,
            warnings=warnings,
            duplicates=list(set(duplicates)),  # Unique tickers
            total_rows=total_rows,
            valid_count=len(valid_rows),
            warning_count=len(warnings),
        )

    def execute_import(
        self, holdings: List[HoldingCreate], user_id: int
    ) -> Tuple[int, int, List[str]]:
        """
        Execute the CSV import by creating TRANSFER_IN transactions.

        Each CSV row becomes a TRANSFER_IN transaction, which automatically
        creates or updates the corresponding holding through the
        TransactionService.

        Args:
            holdings: List of holdings to import
            user_id: User ID

        Returns:
            Tuple of (added_count, updated_count, errors)
        """
        added_count = 0
        updated_count = 0
        errors: List[str] = []

        for holding in holdings:
            try:
                # Check if ticker already exists (for reporting purposes)
                existing = self.portfolio_service.get_holding_by_ticker(
                    holding.ticker, user_id
                )

                # Create TRANSFER_IN transaction (this automatically updates holdings)
                transaction_data = TransactionCreate(
                    ticker=holding.ticker,
                    type="TRANSFER_IN",
                    quantity=holding.quantity,
                    price=holding.purchase_price,
                    fees=Decimal("0.00"),
                    transaction_date=holding.purchase_date,
                    notes="Imported from CSV",
                    cost_basis_known=True,
                )

                self.transaction_service.create_transaction(transaction_data, user_id)

                if existing:
                    updated_count += 1
                    logger.info(f"Updated existing holding via TRANSFER_IN: {holding.ticker}")
                else:
                    added_count += 1
                    logger.info(f"Created new holding via TRANSFER_IN: {holding.ticker}")

            except Exception as e:
                error_msg = f"Failed to import {holding.ticker}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        return added_count, updated_count, errors

    def _map_columns(self, row: dict, column_mapping: dict) -> dict:
        """Map CSV columns to expected field names."""
        mapped = {}
        for field_name, csv_column in column_mapping.items():
            if csv_column in row:
                mapped[field_name] = row[csv_column]
        return mapped

    def _validate_row(
        self, row: dict, row_idx: int, warnings: List[ImportWarning]
    ) -> HoldingCreate | None:
        """
        Validate a single row and create HoldingCreate object.

        Args:
            row: Mapped row data
            row_idx: Row index (for error messages)
            warnings: List to append warnings to

        Returns:
            HoldingCreate object or None if validation fails
        """
        try:
            # Required fields
            ticker = row.get("ticker", "").strip().upper()
            if not ticker:
                warnings.append(
                    ImportWarning(
                        row=row_idx,
                        type="missing_field",
                        message="Missing required field: ticker",
                    )
                )
                return None

            # Validate ticker format (basic)
            if len(ticker) > 20 or not ticker.isalnum():
                if "." not in ticker and "-" not in ticker:  # Allow dots for exchanges
                    warnings.append(
                        ImportWarning(
                            row=row_idx,
                            type="invalid_ticker",
                            message=f"Invalid ticker format: {ticker}",
                            ticker=ticker,
                        )
                    )

            # Parse quantity
            try:
                quantity = Decimal(str(row.get("quantity", "0")))
                if quantity <= 0:
                    warnings.append(
                        ImportWarning(
                            row=row_idx,
                            type="invalid_quantity",
                            message=f"Quantity must be positive: {quantity}",
                            ticker=ticker,
                        )
                    )
                    return None
            except (InvalidOperation, ValueError) as e:
                warnings.append(
                    ImportWarning(
                        row=row_idx,
                        type="invalid_quantity",
                        message=f"Invalid quantity value: {row.get('quantity')}",
                        ticker=ticker,
                    )
                )
                return None

            # Parse purchase price
            try:
                purchase_price = Decimal(str(row.get("purchase_price", "0")))
                if purchase_price <= 0:
                    warnings.append(
                        ImportWarning(
                            row=row_idx,
                            type="invalid_price",
                            message=f"Purchase price must be positive: {purchase_price}",
                            ticker=ticker,
                        )
                    )
                    return None
            except (InvalidOperation, ValueError):
                warnings.append(
                    ImportWarning(
                        row=row_idx,
                        type="invalid_price",
                        message=f"Invalid purchase price value: {row.get('purchase_price')}",
                        ticker=ticker,
                    )
                )
                return None

            # Parse purchase date
            purchase_date_str = row.get("purchase_date", "").strip()
            purchase_date = self._parse_date(purchase_date_str)
            if not purchase_date:
                warnings.append(
                    ImportWarning(
                        row=row_idx,
                        type="invalid_date",
                        message=f"Invalid date format: {purchase_date_str}. "
                        f"Supported formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY",
                        ticker=ticker,
                    )
                )
                return None

            if purchase_date > date.today():
                warnings.append(
                    ImportWarning(
                        row=row_idx,
                        type="future_date",
                        message=f"Purchase date cannot be in the future: {purchase_date}",
                        ticker=ticker,
                    )
                )
                return None

            # Parse currency
            currency = row.get("currency", "USD").upper().strip()
            if currency not in ["EUR", "GBP", "CHF", "USD"]:
                warnings.append(
                    ImportWarning(
                        row=row_idx,
                        type="invalid_currency",
                        message=f"Invalid currency: {currency}. Using USD instead.",
                        ticker=ticker,
                    )
                )
                currency = "USD"

            return HoldingCreate(
                ticker=ticker,
                quantity=quantity,
                purchase_price=purchase_price,
                purchase_date=purchase_date,
                currency=currency,
            )

        except Exception as e:
            logger.error(f"Unexpected error validating row {row_idx}: {e}")
            warnings.append(
                ImportWarning(
                    row=row_idx,
                    type="validation_error",
                    message=f"Validation error: {str(e)}",
                )
            )
            return None

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date string with multiple format support."""
        if not date_str:
            return None

        for fmt in self.SUPPORTED_DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None


def get_csv_import_service(db: Session) -> CSVImportService:
    """Dependency injection for CSV import service."""
    return CSVImportService(db)
