"""
Logging configuration for the application.
"""

import sys
from loguru import logger
from app.core.config import settings
from app.core.correlation import get_correlation_id


def correlation_id_filter(record):
    """
    Add correlation ID to log record if available.

    Args:
        record: The log record to enhance

    Returns:
        True to process the log record
    """
    correlation_id = get_correlation_id()
    record["extra"]["correlation_id"] = correlation_id if correlation_id else "N/A"
    return True


def configure_logging() -> None:
    """
    Configure application logging with Loguru.

    Features:
    - Correlation ID included in all logs
    - Structured JSON format (configurable via LOG_FORMAT env var)
    - Console and file logging
    - Log rotation and retention
    """
    # Remove default handler
    logger.remove()

    # Determine log format
    log_format = getattr(settings, 'LOG_FORMAT', 'text')
    log_level = getattr(settings, 'LOG_LEVEL', 'INFO')

    if log_format == 'json':
        # Structured JSON format for production
        log_format_str = "{extra[correlation_id]} | {time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"
        serialize = True
    else:
        # Human-readable format for development
        log_format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<cyan>{extra[correlation_id]}</cyan> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        serialize = False

    # Console handler
    logger.add(
        sys.stderr,
        format=log_format_str,
        level=log_level,
        colorize=not serialize,
        serialize=serialize,
        filter=correlation_id_filter,
    )

    # File handler
    logger.add(
        "logs/app.log",
        format=log_format_str,
        level=log_level,
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        serialize=serialize,
        filter=correlation_id_filter,
    )

    logger.info("Logging configured successfully")
