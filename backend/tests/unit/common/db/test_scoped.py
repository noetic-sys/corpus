import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from common.db.base import Base
from common.db.scoped import get_session, transaction
from common.db.context import (
    get_current_session,
    in_transaction,
    is_readonly_forced,
    _force_readonly,
)
from packages.companies.models.database.company import CompanyEntity


# Create a separate test engine for scoped tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def scoped_test_engine():
    """Create a test engine for scoped session tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def scoped_session_factory(scoped_test_engine):
    """Create session factory for scoped tests."""
    return async_sessionmaker(
        scoped_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(scope="function")
async def patch_session_factories(scoped_session_factory, monkeypatch):
    """Patch the session factories in scoped.py to use test database."""
    monkeypatch.setattr("common.db.scoped.AsyncSessionLocal", scoped_session_factory)
    monkeypatch.setattr(
        "common.db.scoped.AsyncSessionLocalReadonly", scoped_session_factory
    )
    yield


class TestTransaction:
    """Test the transaction() context manager with real database."""

    async def test_transaction_commits_on_success(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that transaction commits data to database."""
        # Create a company inside a transaction
        async with transaction() as session:
            company = CompanyEntity(name="Transaction Test Company")
            session.add(company)

        # Verify it was committed by reading with a fresh session
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text(
                    "SELECT name FROM companies WHERE name = 'Transaction Test Company'"
                )
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "Transaction Test Company"

    async def test_transaction_rollback_on_exception(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that transaction rolls back on exception."""
        with pytest.raises(ValueError):
            async with transaction() as session:
                company = CompanyEntity(name="Rollback Test Company")
                session.add(company)
                await session.flush()  # Make sure it would have been written
                raise ValueError("Simulated error")

        # Verify it was NOT committed
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text("SELECT name FROM companies WHERE name = 'Rollback Test Company'")
            )
            row = result.fetchone()
            assert row is None

    async def test_transaction_sets_session_in_context(self, patch_session_factories):
        """Test that transaction sets session in context."""
        captured_session = None
        was_in_transaction = None

        async with transaction() as session:
            captured_session = get_current_session(readonly=False)
            was_in_transaction = in_transaction(readonly=False)

        assert captured_session is not None
        assert was_in_transaction is True
        # After exiting, context should be cleared
        assert get_current_session(readonly=False) is None
        assert in_transaction(readonly=False) is False

    async def test_transaction_yields_usable_session(self, patch_session_factories):
        """Test that transaction yields a working session."""
        async with transaction() as session:
            # Should be able to execute queries
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    async def test_nested_transaction_reuses_session(self, patch_session_factories):
        """Test that nested transaction() calls reuse the outer session."""
        sessions_seen = []

        async with transaction() as outer_session:
            sessions_seen.append(outer_session)

            # Nested transaction should reuse the outer session
            async with transaction() as inner_session:
                sessions_seen.append(inner_session)

                # Double nested should also reuse
                async with transaction() as innermost_session:
                    sessions_seen.append(innermost_session)

        # All should be the same session
        assert len(sessions_seen) == 3
        assert all(s is sessions_seen[0] for s in sessions_seen)

    async def test_nested_transaction_does_not_commit(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that nested transaction doesn't commit - outer handles it."""
        async with transaction() as outer_session:
            async with transaction() as inner_session:
                company = CompanyEntity(name="Nested Transaction Company")
                inner_session.add(company)
                await inner_session.flush()

            # Inner transaction exited, but we're still in outer
            # Data should be visible within the transaction
            result = await outer_session.execute(
                text(
                    "SELECT name FROM companies WHERE name = 'Nested Transaction Company'"
                )
            )
            row = result.fetchone()
            assert row is not None

        # After outer commits, verify it's in the database
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text(
                    "SELECT name FROM companies WHERE name = 'Nested Transaction Company'"
                )
            )
            row = result.fetchone()
            assert row is not None

    async def test_nested_transaction_rollback_handled_by_outer(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that exception in nested transaction rolls back outer transaction."""
        with pytest.raises(ValueError):
            async with transaction() as outer_session:
                company1 = CompanyEntity(name="Outer Company")
                outer_session.add(company1)
                await outer_session.flush()

                async with transaction() as inner_session:
                    company2 = CompanyEntity(name="Inner Company")
                    inner_session.add(company2)
                    await inner_session.flush()
                    raise ValueError("Error in nested transaction")

        # Both should be rolled back
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text(
                    "SELECT name FROM companies WHERE name IN ('Outer Company', 'Inner Company')"
                )
            )
            rows = result.fetchall()
            assert len(rows) == 0

    async def test_nested_transaction_data_visible_to_outer(
        self, patch_session_factories
    ):
        """Test that data created in nested transaction is visible to outer."""
        async with transaction() as outer_session:
            # Create data in nested transaction
            async with transaction() as inner_session:
                company = CompanyEntity(name="Visible Company")
                inner_session.add(company)
                await inner_session.flush()

            # Should be visible in outer transaction after inner exits
            result = await outer_session.execute(
                text("SELECT name FROM companies WHERE name = 'Visible Company'")
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "Visible Company"


class TestGetSession:
    """Test the get_session() context manager with real database."""

    async def test_standalone_get_session_commits(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test standalone get_session acquires session and commits."""
        async with get_session() as session:
            company = CompanyEntity(name="GetSession Test Company")
            session.add(company)

        # Verify it was committed
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text(
                    "SELECT name FROM companies WHERE name = 'GetSession Test Company'"
                )
            )
            row = result.fetchone()
            assert row is not None

    async def test_standalone_get_session_rollback_on_exception(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test standalone get_session rolls back on exception."""
        with pytest.raises(ValueError):
            async with get_session() as session:
                company = CompanyEntity(name="GetSession Rollback Company")
                session.add(company)
                await session.flush()
                raise ValueError("Simulated error")

        # Verify it was NOT committed
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text(
                    "SELECT name FROM companies WHERE name = 'GetSession Rollback Company'"
                )
            )
            row = result.fetchone()
            assert row is None

    async def test_get_session_reuses_transaction_session(
        self, patch_session_factories
    ):
        """Test get_session reuses existing transaction session."""
        sessions_seen = []

        async with transaction() as tx_session:
            sessions_seen.append(tx_session)

            # Nested get_session calls should reuse the transaction session
            async with get_session() as s1:
                sessions_seen.append(s1)
            async with get_session() as s2:
                sessions_seen.append(s2)
            async with get_session() as s3:
                sessions_seen.append(s3)

        # All should be the same session
        assert all(s is sessions_seen[0] for s in sessions_seen)

    async def test_get_session_does_not_commit_when_reusing(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that nested get_session doesn't commit - transaction handles it."""
        async with transaction() as tx_session:
            async with get_session() as session:
                company = CompanyEntity(name="Nested Session Company")
                session.add(company)
                await session.flush()  # Flush to make visible within transaction
            # At this point, get_session has exited but we're still in transaction

            # Verify data is visible within transaction but not yet committed
            result = await tx_session.execute(
                text("SELECT name FROM companies WHERE name = 'Nested Session Company'")
            )
            row = result.fetchone()
            assert row is not None  # Visible in transaction

        # After transaction commits, verify it's in the database
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text("SELECT name FROM companies WHERE name = 'Nested Session Company'")
            )
            row = result.fetchone()
            assert row is not None


class TestSessionReuse:
    """Test session reuse behavior within transactions."""

    async def test_multiple_operations_in_transaction_share_session(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that multiple get_session calls within transaction all work together."""
        async with transaction():
            # Multiple operations, all should use the same session
            async with get_session() as session:
                company1 = CompanyEntity(name="Multi Op Company 1")
                session.add(company1)

            async with get_session() as session:
                company2 = CompanyEntity(name="Multi Op Company 2")
                session.add(company2)

            async with get_session() as session:
                company3 = CompanyEntity(name="Multi Op Company 3")
                session.add(company3)

        # All three should be committed together
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text(
                    "SELECT COUNT(*) FROM companies WHERE name LIKE 'Multi Op Company%'"
                )
            )
            count = result.scalar()
            assert count == 3

    async def test_standalone_sessions_are_independent(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that standalone get_sessions are independent."""
        # Each standalone get_session gets its own session
        async with get_session() as s1:
            async with get_session() as s2:
                # These are NOT the same session (no outer transaction)
                # But both can execute queries
                r1 = await s1.execute(text("SELECT 1"))
                r2 = await s2.execute(text("SELECT 2"))
                assert r1.scalar() == 1
                assert r2.scalar() == 2


class TestConcurrentTransactions:
    """Test behavior with concurrent transactions."""

    async def test_concurrent_transactions_are_isolated(self, patch_session_factories):
        """Test that concurrent transactions have isolated sessions."""
        results = {}

        async def task_with_transaction(task_id: str, delay: float):
            async with transaction() as session:
                await asyncio.sleep(delay)
                current = get_current_session(readonly=False)
                results[task_id] = current is session

        await asyncio.gather(
            task_with_transaction("tx1", 0.01),
            task_with_transaction("tx2", 0.005),
            task_with_transaction("tx3", 0.015),
        )

        assert results["tx1"] is True
        assert results["tx2"] is True
        assert results["tx3"] is True

    async def test_concurrent_transactions_dont_interfere(
        self, patch_session_factories, scoped_session_factory
    ):
        """Test that concurrent transactions don't interfere with each other."""
        results = {"success": [], "failed": []}

        async def create_company(name: str, should_fail: bool):
            try:
                async with transaction() as session:
                    company = CompanyEntity(name=name)
                    session.add(company)
                    if should_fail:
                        raise ValueError("Intentional failure")
                results["success"].append(name)
            except ValueError:
                results["failed"].append(name)

        await asyncio.gather(
            create_company("Concurrent Company 1", should_fail=False),
            create_company("Concurrent Company 2", should_fail=True),
            create_company("Concurrent Company 3", should_fail=False),
        )

        assert "Concurrent Company 1" in results["success"]
        assert "Concurrent Company 2" in results["failed"]
        assert "Concurrent Company 3" in results["success"]

        # Verify only successful ones are in DB
        async with scoped_session_factory() as verify_session:
            result = await verify_session.execute(
                text(
                    "SELECT name FROM companies WHERE name LIKE 'Concurrent Company%' ORDER BY name"
                )
            )
            rows = result.fetchall()
            names = [r[0] for r in rows]
            assert "Concurrent Company 1" in names
            assert "Concurrent Company 2" not in names
            assert "Concurrent Company 3" in names


class TestReadonlyBehavior:
    """Test readonly session behavior."""

    async def test_readonly_forced_is_respected(self, patch_session_factories):
        """Test that get_session respects readonly forced flag."""
        token = _force_readonly.set(True)
        try:
            async with get_session() as session:
                # Should be using readonly context
                assert is_readonly_forced() is True
                # Session should still work for reads
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            _force_readonly.reset(token)
