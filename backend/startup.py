#!/usr/bin/env python3
"""
Backend startup script.

This script:
1. Waits for database to be ready
2. Runs database migrations automatically
3. Starts the FastAPI application

This ensures the database is always up-to-date when the backend starts.
"""

import time
import sys
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command
from app.core.config import settings
from loguru import logger
import uvicorn


def wait_for_db(max_retries=30, retry_interval=2):
    """Wait for database to be ready."""
    logger.info(f"Waiting for database at {settings.DATABASE_URL}...")

    for attempt in range(max_retries):
        try:
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.success("Database is ready!")
            return True
        except Exception as e:
            logger.warning(
                f"Database not ready (attempt {attempt + 1}/{max_retries}): {e}"
            )
            time.sleep(retry_interval)

    logger.error("Database failed to become ready in time")
    return False


def run_migrations():
    """Run database migrations."""
    try:
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.success("Migrations completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def start_server():
    """Start the FastAPI server."""
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}...")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # Disable in production, enable for dev
        log_level="info",
    )


if __name__ == "__main__":
    # Wait for database
    if not wait_for_db():
        logger.error("Exiting due to database connection failure")
        sys.exit(1)

    # Run migrations
    if not run_migrations():
        logger.error("Exiting due to migration failure")
        sys.exit(1)

    # Start server
    start_server()
