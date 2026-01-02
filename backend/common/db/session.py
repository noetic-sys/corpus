from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import pool
import time
from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)

# Import all models to ensure they are registered with SQLAlchemy
# Replace postgresql:// with postgresql+asyncpg:// for async support
# nuclear: .append("?prepared_statement_cache_size=0")
ASYNC_DATABASE_URL = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Configure engine based on pool type
# NullPool (db_use_nullpool=True): No pooling, new connection per operation (for workers)
# Default pool: Connection pooling (for API servers with concurrent requests)
engine_kwargs = {
    "echo": settings.debug,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "connect_args": {
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },
}

if settings.db_use_nullpool:
    logger.info("Using NullPool - no connection pooling (worker mode)")
    engine_kwargs["poolclass"] = pool.NullPool
else:
    logger.info(
        f"Using connection pooling - pool_size={settings.db_pool_size}, max_overflow={settings.db_pool_overflow}"
    )
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_pool_overflow

engine = create_async_engine(ASYNC_DATABASE_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Readonly engine - separate for read-heavy operations
# readonly_engine = create_async_engine(
#     ASYNC_DATABASE_URL,
#     echo=settings.debug,
#     pool_size=5,
#     max_overflow=10,
#     pool_pre_ping=True,
#     pool_recycle=3600,
#     connect_args={
#         "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
#     },
# )

AsyncSessionLocalReadonly = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# @event.listens_for(Session, "after_flush")
# def log_flush(session, flush_context):
#     print("WE FLUSHED")
#     session.info["flushed"] = True


# @event.listens_for(Session, "after_commit")
# @event.listens_for(Session, "after_rollback")
# def reset_flushed(session):
#     print("WE RESET FLUSHED")
#     if "flushed" in session.info:
#         del session.info["flushed"]

# decides if we commit changes or not. perf improvements
# def has_uncommitted_changes(session):
#     var =  (
#         any(session.new)
#         or any(session.deleted)
#         or any([x for x in session.dirty if session.is_modified(x)])
#         or session.info.get("flushed", False)
#     )
#     print(f"Has uncommitted: {var}")
#     return var


async def get_db():
    start = time.perf_counter()
    async with AsyncSessionLocal() as session:
        acquire_time = time.perf_counter() - start
        logger.info(
            f"Session acquire: {acquire_time * 1000:.2f}ms, debug: {settings.debug}"
        )

        try:
            yield session

            commit_start = time.perf_counter()
            did_commit = True
            await session.commit()
            # print("Always committing")
            commit_time = time.perf_counter() - commit_start
            logger.info(
                f"Commit time: {commit_time * 1000:.2f}ms did_commit: {did_commit}"
            )
        except Exception as e:
            # print("Rolling back because of error")
            logger.error(f"Rolling back due to error {e}")
            await session.rollback()
            raise


async def get_db_readonly():
    """Readonly session - skips commit overhead for read-only operations.

    Use for read-heavy endpoints. When you add a read replica,
    just change readonly_engine's connection string.
    Works correctly with PGBouncer transaction pooling.
    """
    start = time.perf_counter()
    async with AsyncSessionLocalReadonly() as session:
        acquire_time = time.perf_counter() - start
        logger.info(f"Readonly session acquire: {acquire_time * 1000:.2f}ms")

        try:
            yield session
            # No explicit commit for readonly - connection released by context manager
        except Exception as e:
            logger.error(f"Error in readonly session: {e}")
            await session.rollback()
            raise


async def init_db():
    # This will be used by Alembic migrations
    pass
