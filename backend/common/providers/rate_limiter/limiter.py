"""Global rate limiter instance for SlowAPI."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from common.core.config import settings

# Redis-backed rate limiter for distributed rate limiting across all API pods
# Multiple limits: both must be satisfied (whichever is hit first applies)
# - 10/second: Prevents thundering herd (e.g., workspace loading 300 cells at once)
# - 300/minute: Sustained rate limit (5 req/sec average)
# Using Redis ensures users can't bypass limits by hitting different pods
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10/second", "300/minute"],
    storage_uri=settings.redis_connection_url,
)
