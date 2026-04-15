"""
Correlation ID management for request tracing.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable to store correlation ID per request
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.

    Returns:
        The correlation ID for the current request, or None if not set
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current request.

    Args:
        correlation_id: The correlation ID to set
    """
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.

    Returns:
        A new UUID4 correlation ID as a string
    """
    return str(uuid.uuid4())
