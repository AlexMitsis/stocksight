"""
Redis caching utilities for application.

This module provides:
1. Standard Redis caching with @cache decorator for tool-level caching
2. Cache pattern clearing utilities

Note: We intentionally do NOT use LLM response caching (LangCache) because
stock data requires real-time accuracy. Tool-level caching with appropriate
TTLs is used instead (e.g., 60s for prices, 24h for balance sheets).
"""

import redis
import json
import hashlib
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime
from loguru import logger
from app.core.config import settings


# Redis client (None if Redis not available)
redis_client: Optional[redis.Redis] = None

if settings.REDIS_URL:
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )
        # Test connection
        redis_client.ping()
        logger.info(f"Redis connected: {settings.REDIS_URL}")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Caching disabled.")
        redis_client = None
else:
    logger.info("No REDIS_URL configured. Caching disabled.")


def cache(ttl: int = 300, include_timestamp: bool = True):
    """
    Cache decorator for functions.

    Args:
        ttl: Time to live in seconds
        include_timestamp: If True, adds 'cached_at' timestamp to response

    Usage:
        @cache(ttl=3600, include_timestamp=True)
        def expensive_function(arg1, arg2):
            return {"data": "result"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # If Redis not available, just call function
            if redis_client is None:
                return func(*args, **kwargs)

            try:
                # Create cache key from function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_data = ":".join(key_parts)
                cache_key = f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"

                # Try to get from cache
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache HIT: {func.__name__}")
                    result = json.loads(cached)
                    return result

                # Call function if not cached
                logger.info(f"Cache MISS: {func.__name__}")
                result = func(*args, **kwargs)

                # Add timestamp if requested and result is a dict
                if include_timestamp and isinstance(result, dict):
                    result['cached_at'] = datetime.utcnow().isoformat() + 'Z'

                # Store in cache
                redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(result)
                )

                logger.debug(f"Cached {func.__name__} for {ttl}s")

                return result

            except Exception as e:
                logger.error(f"Cache error in {func.__name__}: {e}")
                # On cache error, just call function
                return func(*args, **kwargs)

        return wrapper
    return decorator


def clear_cache_pattern(pattern: str) -> int:
    """
    Clear all cache keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., "cache:get_stock_price:*")

    Returns:
        Number of keys deleted
    """
    if redis_client is None:
        return 0

    try:
        keys = redis_client.keys(f"cache:{pattern}")
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"Cleared {deleted} cache keys matching '{pattern}'")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return 0


