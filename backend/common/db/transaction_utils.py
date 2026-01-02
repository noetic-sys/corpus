"""Database transaction utilities for services."""

import functools
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import ResourceClosedError


@asynccontextmanager
async def transaction(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    if db_session.in_transaction():
        # If already in a transaction, create a savepoint (nested transaction)
        savepoint = await db_session.begin_nested()
        try:
            yield
            # Try to commit savepoint, but handle case where it's already closed
            try:
                await savepoint.commit()
            except ResourceClosedError:
                # Savepoint is already closed, which is fine for successful completion
                pass
        except Exception:
            # Try to rollback savepoint, but handle case where it's already closed
            try:
                await savepoint.rollback()
            except ResourceClosedError:
                # Savepoint is already closed, just re-raise the original exception
                pass
            raise
    else:
        # Start a new transaction if none exists
        await db_session.begin()
        try:
            yield
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise


def transactional(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs) -> Any:
        if not hasattr(self, "db_session"):
            raise AttributeError(
                f"Service {self.__class__.__name__} must have 'db_session' attribute "
                "to use @transactional decorator"
            )

        async with transaction(self.db_session):
            return await func(self, *args, **kwargs)

    return wrapper


class TransactionMixin:
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        """Context manager for database transactions."""
        if not hasattr(self, "db_session"):
            raise AttributeError(
                f"Service {self.__class__.__name__} must have 'db_session' attribute "
                "to use transaction() method"
            )

        async with transaction(self.db_session):
            yield
