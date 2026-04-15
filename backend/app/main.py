"""
Main FastAPI application entry point.
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.middleware import LoggingMiddleware
from app.routers import chat, auth, portfolio, market_data
from app.services.holdings_migration_service import HoldingsMigrationService

# Configure logging
configure_logging()
logger.info("Application starting...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.

    On startup:
    - Migrates orphaned holdings to TRANSFER_IN transactions
    """
    # Startup
    logger.info("Running startup tasks...")

    # Migrate orphaned holdings (holdings without backing transactions)
    try:
        db = SessionLocal()
        migration_service = HoldingsMigrationService(db)
        migrated_count = migration_service.migrate_orphaned_holdings()
        if migrated_count > 0:
            logger.info(f"Startup migration: Created {migrated_count} TRANSFER_IN transactions for orphaned holdings")
        else:
            logger.info("Startup migration: No orphaned holdings found")
        db.close()
    except Exception as e:
        logger.error(f"Failed to run holdings migration on startup: {e}")
        # Don't prevent app from starting

    yield

    # Shutdown
    logger.info("Application shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Stock Analysis API",
    description="AI-powered stock analysis and investment assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# Add logging middleware (should be first to track all requests)
app.add_middleware(LoggingMiddleware)

# Configure CORS
cors_origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(portfolio.router)
app.include_router(market_data.router)

# Mount Prometheus metrics endpoint
# This exposes RAG performance metrics at /metrics
# for scraping by Prometheus or viewing directly
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
logger.info("Prometheus metrics endpoint mounted at /metrics")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Stock Analysis API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
