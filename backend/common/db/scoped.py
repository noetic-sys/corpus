"""
Operation-scoped database sessions.

Provides lazy session acquisition that releases connections immediately
after each operation, preventing connection holding during external calls
(AI, HTTP, file I/O, etc.)

Usage:
    # Single operation - acquires and releases immediately
    async with get_session() as session:
        result = await session.get(Model, id)
    # Connection released here

    # Multiple operations in a transaction - share one session
    async with transaction():
        await repo.save(thing1)
        await repo.save(thing2)
    # Commits together, then releases

    # Force readonly for a call chain (use decorator)
    from common.db.context import readonly

    @readonly
    async def read_heavy_operation():
        ...  # All get_session() calls use read session

See also:
    - common/db/context.py: Decorators (@readonly, @transactional)
    - common/db/session.py: Legacy request-scoped sessions (get_db)
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from common.core.otel_axiom_exporter import get_logger
from common.db.session import AsyncSessionLocal, AsyncSessionLocalReadonly
from common.db.context import (
    get_current_session,
    set_current_session,
    reset_current_session,
    is_readonly_forced,
)

logger = get_logger(__name__)


@asynccontextmanager
async def transaction(readonly: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """
    Explicit transaction boundary.

    All DB operations inside share one session/connection.
    Commits on success (unless readonly), rolls back on exception.

    Args:
        readonly: If True, uses readonly session and skips commit.
                  Also respects @readonly decorator if applied to caller.

    Yields:
        The session for this transaction

    Usage:
        async with transaction():
            await repo.save(thing1)
            await repo.save(thing2)
            # Commits together at end

        async with transaction(readonly=True):
            # Read-only transaction for consistent snapshot
            data = await repo.get_all()
            # No commit, just releases

    Raises:
        Exception: Re-raises any exception after rollback
    """
    effective_readonly = readonly or is_readonly_forced()
    session_factory = (
        AsyncSessionLocalReadonly if effective_readonly else AsyncSessionLocal
    )

    start = time.perf_counter()
    async with session_factory() as session:
        acquire_time = time.perf_counter() - start
        logger.debug(
            f"Transaction session acquire: {acquire_time * 1000:.2f}ms, readonly={effective_readonly}"
        )

        token = set_current_session(session, readonly=effective_readonly)
        try:
            yield session
            if not effective_readonly:
                commit_start = time.perf_counter()
                await session.commit()
                commit_time = time.perf_counter() - commit_start
                logger.debug(f"Transaction commit: {commit_time * 1000:.2f}ms")
        except Exception as e:
            logger.error(f"Transaction rollback due to: {e}")
            await session.rollback()
            raise
        finally:
            reset_current_session(token, readonly=effective_readonly)


@asynccontextmanager
async def get_session(readonly: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a session for a single DB operation.

    This is the primary interface for repositories. It provides lazy session
    management that:
    - Reuses session if inside a transaction() block
    - Otherwise acquires a new session, auto-commits, and releases immediately

    This prevents holding connections during external calls (AI, HTTP, etc.)

    Args:
        readonly: If True, uses readonly session (for read replicas).
                  Also respects @readonly decorator if applied to caller.

    Yields:
        A session for the operation

    Usage:
        # In a repository method
        async def get(self, id: int):
            async with get_session(readonly=True) as session:
                return await session.get(Model, id)
            # Connection released here

        # If called inside a transaction(), reuses that session
        async with transaction():
            await repo.save(thing1)  # Uses transaction's session
            await repo.save(thing2)  # Same session
            # Commits together at end
    """
    effective_readonly = readonly or is_readonly_forced()
    existing = get_current_session(readonly=effective_readonly)

    if existing:
        # Inside a transaction - reuse session, don't commit (transaction handles it)
        logger.debug("Reusing existing transaction session")
        yield existing
    else:
        # Standalone operation - acquire, commit, release
        session_factory = (
            AsyncSessionLocalReadonly if effective_readonly else AsyncSessionLocal
        )

        start = time.perf_counter()
        async with session_factory() as session:
            acquire_time = time.perf_counter() - start
            logger.debug(
                f"Operation session acquire: {acquire_time * 1000:.2f}ms, readonly={effective_readonly}"
            )

            try:
                yield session
                if not effective_readonly:
                    commit_start = time.perf_counter()
                    await session.commit()
                    commit_time = time.perf_counter() - commit_start
                    logger.debug(f"Operation commit: {commit_time * 1000:.2f}ms")
            except Exception as e:
                logger.error(f"Operation rollback due to: {e}")
                await session.rollback()
                raise
            # Connection released here when context manager exits
