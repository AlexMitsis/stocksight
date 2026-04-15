"""
Logging middleware for request/response tracking with correlation IDs.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.core.correlation import (
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs and log request/response information.

    Features:
    - Adds/extracts correlation ID from X-Correlation-ID header
    - Logs incoming requests with method, path, correlation ID
    - Logs responses with status code, duration
    - Adds correlation ID to response headers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request with correlation ID tracking and logging.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            The response with correlation ID header added
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()

        # Set in context for this request
        set_correlation_id(correlation_id)

        # Log request
        logger.bind(correlation_id=correlation_id).info(
            f"Request started: {request.method} {request.url.path}"
        )

        # Record start time
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.bind(correlation_id=correlation_id).info(
                f"Request completed: {response.status_code} in {duration:.3f}s"
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.bind(correlation_id=correlation_id).error(
                f"Request failed: {request.method} {request.url.path} "
                f"in {duration:.3f}s - {type(e).__name__}: {str(e)}"
            )

            # Re-raise to let FastAPI's error handling take over
            raise
