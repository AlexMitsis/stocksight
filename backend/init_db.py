#!/usr/bin/env python3
"""
Database initialization script.

This script initializes the database by running all pending migrations.
Use this script to set up the database for the first time or after pulling
new migrations.

Usage:
    python init_db.py
    # or
    uv run python init_db.py
"""

from alembic.config import Config
from alembic import command
from app.core.config import settings
from loguru import logger


def init_database():
    """Initialize the database by running all migrations."""
    try:
        logger.info("Initializing database...")
        logger.info(f"Database URL: {settings.DATABASE_URL}")

        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")

        # Run migrations
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")

        logger.success("Database initialized successfully!")
        logger.info("All migrations applied.")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    init_database()
