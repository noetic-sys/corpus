import functools
import hashlib
import json
from typing import Callable, Optional, List, Type
from pydantic import BaseModel

from common.core.otel_axiom_exporter import get_logger
from .factory import get_cache_provider

logger = get_logger(__name__)


def _generate_cache_key(
    func: Callable, args: tuple, kwargs: dict, custom_key: Optional[str] = None
) -> str:
    """Generate a cache key for a function call. Never fails - returns fallback on error."""
    try:
        if custom_key:
            return custom_key

        # Get class and method name
        if args and hasattr(args[0], "__class__"):
            # Instance method
            class_name = args[0].__class__.__name__
            method_name = func.__name__
            # Remove 'self' from args for key generation
            key_args = args[1:]
        else:
            # Function or static method
            class_name = func.__module__.split(".")[-1]
            method_name = func.__name__
            key_args = args

        # Create a deterministic hash of arguments
        args_str = ""
        if key_args or kwargs:
            # Convert args and kwargs to a deterministic string
            args_data = {"args": key_args, "kwargs": dict(sorted(kwargs.items()))}
            args_json = json.dumps(args_data, sort_keys=True, default=str)
            args_hash = hashlib.md5(args_json.encode()).hexdigest()[:8]
            args_str = f":{args_hash}"

        return f"{class_name}:{method_name}{args_str}"
    except Exception as e:
        # Fallback to simple key if anything fails
        logger.warning(f"Cache key generation failed for {func.__name__}: {e}")
        return f"{func.__name__}:fallback"


def cache(model_type: Type, ttl: int = 3600, key_generator: Optional[Callable] = None):
    """
    Cache decorator for async methods/functions.

    Args:
        model_type: Pydantic model type for serialization/deserialization (REQUIRED)
        ttl: Time to live in seconds (default: 1 hour)
        key_generator: Optional custom key generator function
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Wrap everything in try-catch to ensure we NEVER fail due to caching
            try:
                cache_provider = get_cache_provider()

                # Generate cache key with bulletproof fallback
                cache_key = None
                try:
                    if key_generator:
                        try:
                            if args and hasattr(args[0], "__class__"):
                                # Instance method - skip self and pass only actual function args
                                cache_key = key_generator(*args[1:], **kwargs)
                            else:
                                # Function - pass all args
                                cache_key = key_generator(*args, **kwargs)
                        except Exception as e:
                            logger.warning(
                                f"Custom key generator failed for {func.__name__}: {e}"
                            )
                            cache_key = _generate_cache_key(func, args, kwargs)
                    else:
                        cache_key = _generate_cache_key(func, args, kwargs)
                except Exception as e:
                    logger.warning(
                        f"Cache key generation completely failed for {func.__name__}: {e}"
                    )
                    # Continue without cache key - will skip caching entirely

                # Try to get from cache first (only if we have a valid key)
                if cache_key:
                    try:
                        cached_value = await cache_provider.get(cache_key)
                        if cached_value is not None:
                            logger.debug(f"Cache hit for key: {cache_key}")
                            # Check if it's a Pydantic model type or regular type
                            if issubclass(model_type, BaseModel):
                                # Pydantic model - reconstruct from dict
                                if isinstance(cached_value, list):
                                    return [
                                        model_type.model_validate(item)
                                        for item in cached_value
                                    ]
                                else:
                                    return model_type.model_validate(cached_value)
                            else:
                                # Regular type - return as is
                                return cached_value
                    except Exception as e:
                        logger.warning(f"Cache get failed for key {cache_key}: {e}")
                        # Continue to execute function

            except Exception as e:
                # If ANYTHING in the cache setup fails, log and continue
                logger.warning(f"Cache decorator setup failed for {func.__name__}: {e}")

            # Execute the original function (this should NEVER be wrapped in try-catch)
            # Cache miss or cache failure - execute function
            logger.debug(
                f"Cache miss or cache error for {func.__name__} - executing function"
            )
            result = await func(*args, **kwargs)

            # Try to store in cache (best effort, never fail)
            if cache_key:
                try:
                    cache_value = result
                    if result is not None and issubclass(model_type, BaseModel):
                        # Convert Pydantic models to dict for serialization
                        if isinstance(result, list):
                            # List of Pydantic models
                            cache_value = [item.model_dump() for item in result]
                        else:
                            # Single Pydantic model
                            cache_value = result.model_dump()

                    cache_provider = get_cache_provider()
                    await cache_provider.set(cache_key, cache_value, ttl)
                    logger.debug(f"Cached result for key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set failed for key {cache_key}: {e}")
                    # Continue regardless

            return result

        return wrapper

    return decorator


def cache_invalidate(patterns: List[str]):
    """
    Cache invalidation decorator that clears cache patterns after function execution.

    Args:
        patterns: List of cache key patterns to invalidate (e.g., ["ai_model:*"])
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the function first (NEVER wrap this in try-catch)
            result = await func(*args, **kwargs)

            # Then try to invalidate cache patterns (best effort, never fail)
            try:
                cache_provider = get_cache_provider()

                for pattern in patterns:
                    try:
                        deleted_count = await cache_provider.delete_pattern(pattern)
                        logger.info(
                            f"Invalidated {deleted_count} cache keys matching pattern: {pattern}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Cache invalidation failed for pattern {pattern}: {e}"
                        )
                        # Continue with next pattern

            except Exception as e:
                # If cache provider setup fails entirely, log and continue
                logger.warning(
                    f"Cache invalidation setup failed for {func.__name__}: {e}"
                )

            return result

        return wrapper

    return decorator


def cache_key_for_method(class_name: str, method_name: str, *args) -> str:
    """
    Helper function to generate cache keys for specific methods.
    Useful for custom key generators.

    Args:
        class_name: Name of the class
        method_name: Name of the method
        *args: Method arguments

    Returns:
        Generated cache key
    """
    args_str = ""
    if args:
        args_json = json.dumps(args, sort_keys=True, default=str)
        args_hash = hashlib.md5(args_json.encode()).hexdigest()[:8]
        args_str = f":{args_hash}"

    return f"{class_name}:{method_name}{args_str}"
