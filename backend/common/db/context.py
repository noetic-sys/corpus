"""
Database session context management.

Provides lazy session acquisition that:
- Reuses sessions within explicit transactions
- Auto-acquires/releases for one-off operations
- Supports reader/writer separation
- Works alongside existing FastAPI dependency injection

Usage:
    # In repositories - auto-manages sessions
    async with get_session() as session:
        result = await session.execute(query)

    # Explicit transaction - multiple ops share one session
    async with transaction():
        await repo.save(thing1)
        await repo.save(thing2)  # Same session, commits together

    # Force readonly for entire call chain
    @readonly
    async def read_heavy_operation():
        ...  # All DB ops use read session
"""

from contextvars import ContextVar
from functools import wraps
from typing import Optional, Callable, TypeVar, ParamSpec
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class SessionMode(Enum):
    """Session mode for the current context."""

    WRITE = "write"
    READ = "read"


# =============================================================================
# Context Variables
# =============================================================================

# Holds the current write session (if inside a write transaction)
_write_session: ContextVar[Optional[AsyncSession]] = ContextVar(
    "db_write_session", default=None
)

# Holds the current read session (if inside a read transaction)
_read_session: ContextVar[Optional[AsyncSession]] = ContextVar(
    "db_read_session", default=None
)

# Forces all operations in this context to use readonly
_force_readonly: ContextVar[bool] = ContextVar("db_force_readonly", default=False)


# =============================================================================
# Context Accessors
# =============================================================================


def is_readonly_forced() -> bool:
    """Check if current context is forced to readonly."""
    return _force_readonly.get()


def get_current_session(readonly: bool = False) -> Optional[AsyncSession]:
    """
    Get the current session from context, if any.

    Args:
        readonly: If True, get read session. If False, get write session.
                  Note: if readonly is forced via decorator, always returns read session.

    Returns:
        The current session if inside a transaction, None otherwise.
    """
    effective_readonly = readonly or is_readonly_forced()
    if effective_readonly:
        return _read_session.get()
    return _write_session.get()


def set_current_session(session: AsyncSession, readonly: bool = False) -> object:
    """
    Set session in context.

    Args:
        session: The session to set
        readonly: Whether this is a read session

    Returns:
        Token for resetting the context variable
    """
    if readonly:
        return _read_session.set(session)
    return _write_session.set(session)


def reset_current_session(token: object, readonly: bool = False) -> None:
    """
    Reset session context using token from set_current_session.

    Args:
        token: The token returned by set_current_session
        readonly: Whether this was a read session
    """
    if readonly:
        _read_session.reset(token)
    else:
        _write_session.reset(token)


def in_transaction(readonly: bool = False) -> bool:
    """
    Check if we're currently inside a transaction.

    Args:
        readonly: Check for read transaction (True) or write transaction (False)

    Returns:
        True if inside a transaction of the specified type
    """
    return get_current_session(readonly=readonly) is not None


# =============================================================================
# Decorators
# =============================================================================

P = ParamSpec("P")
T = TypeVar("T")


def readonly(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator that forces all DB operations in this call chain to use readonly sessions.

    Useful for read-heavy operations where you want to ensure no writes occur
    and potentially route to a read replica.

    Usage:
        @readonly
        async def get_dashboard_data(company_id: int):
            # All repo calls here will use read session
            users = await user_repo.get_all(company_id)
            stats = await stats_repo.get_summary(company_id)
            return {"users": users, "stats": stats}
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        token = _force_readonly.set(True)
        try:
            return await func(*args, **kwargs)
        finally:
            _force_readonly.reset(token)

    return wrapper


def transactional(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator that wraps function in an explicit transaction.

    All DB operations within the decorated function share one session/connection.
    The transaction commits on success, rolls back on exception.

    Respects @readonly decorator - if applied, uses readonly session.

    Usage:
        @transactional
        async def transfer_funds(from_id: int, to_id: int, amount: float):
            # These share a session, commit together or rollback together
            await account_repo.debit(from_id, amount)
            await account_repo.credit(to_id, amount)

        @readonly
        @transactional
        async def generate_report(company_id: int):
            # Read-only transaction for consistent snapshot
            data = await report_repo.get_all_data(company_id)
            return process_report(data)
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        from common.db.scoped import transaction as tx  # noqa: PLC0415

        async with tx():
            return await func(*args, **kwargs)

    return wrapper
