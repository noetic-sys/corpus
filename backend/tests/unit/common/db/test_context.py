import pytest
import asyncio

from common.db.context import (
    is_readonly_forced,
    get_current_session,
    set_current_session,
    reset_current_session,
    in_transaction,
    readonly,
    _force_readonly,
)


class TestContextVariables:
    """Test context variable behavior."""

    def test_default_state(self):
        """Test that context variables have correct default values."""
        assert is_readonly_forced() is False
        assert get_current_session(readonly=False) is None
        assert get_current_session(readonly=True) is None

    def test_in_transaction_false_by_default(self):
        """Test in_transaction returns False when no session is set."""
        assert in_transaction(readonly=False) is False
        assert in_transaction(readonly=True) is False


class TestContextIsolation:
    """Test that context variables are isolated between concurrent async tasks."""

    async def test_concurrent_tasks_have_isolated_contexts(self, test_db):
        """Test that concurrent async tasks don't share context."""
        results = {}

        async def task_with_session(task_id: str, delay: float):
            # Each task sets its own session in context
            token = set_current_session(test_db, readonly=False)
            await asyncio.sleep(delay)

            # After sleeping, we should still see our own session
            current = get_current_session(readonly=False)
            results[task_id] = current is test_db

            reset_current_session(token, readonly=False)

        # Run tasks concurrently - they should each see their own context
        await asyncio.gather(
            task_with_session("task1", 0.01),
            task_with_session("task2", 0.005),
            task_with_session("task3", 0.015),
        )

        assert results["task1"] is True
        assert results["task2"] is True
        assert results["task3"] is True

    async def test_nested_calls_inherit_context(self, test_db):
        """Test that nested async calls within same task inherit context."""
        nested_result = None

        async def nested_function():
            nonlocal nested_result
            current = get_current_session(readonly=False)
            nested_result = current is test_db

        token = set_current_session(test_db, readonly=False)
        await nested_function()
        reset_current_session(token, readonly=False)

        assert nested_result is True

    async def test_readonly_flag_isolated_between_tasks(self):
        """Test that readonly force flag is isolated between concurrent tasks."""
        results = {}

        async def check_readonly(task_id: str, set_readonly: bool):
            if set_readonly:
                token = _force_readonly.set(True)

            await asyncio.sleep(0.01)
            results[task_id] = is_readonly_forced()

            if set_readonly:
                _force_readonly.reset(token)

        await asyncio.gather(
            check_readonly("readonly_task", True),
            check_readonly("normal_task", False),
        )

        assert results["readonly_task"] is True
        assert results["normal_task"] is False


class TestReadonlyDecorator:
    """Test the @readonly decorator."""

    async def test_readonly_decorator_sets_force_flag(self):
        """Test that @readonly decorator sets force_readonly during execution."""
        captured_value = None

        @readonly
        async def readonly_function():
            nonlocal captured_value
            captured_value = is_readonly_forced()

        assert is_readonly_forced() is False
        await readonly_function()
        assert captured_value is True
        assert is_readonly_forced() is False

    async def test_readonly_decorator_resets_on_exception(self):
        """Test that @readonly decorator resets flag even on exception."""

        @readonly
        async def failing_function():
            raise ValueError("test error")

        assert is_readonly_forced() is False

        with pytest.raises(ValueError):
            await failing_function()

        assert is_readonly_forced() is False

    async def test_readonly_decorator_with_args(self):
        """Test that @readonly decorator preserves function arguments."""

        @readonly
        async def function_with_args(a: int, b: str, c: bool = False):
            return (a, b, c, is_readonly_forced())

        result = await function_with_args(1, "test", c=True)
        assert result == (1, "test", True, True)

    async def test_nested_readonly_decorators(self):
        """Test nested @readonly decorated functions."""
        outer_value = None
        inner_value = None

        @readonly
        async def inner_function():
            nonlocal inner_value
            inner_value = is_readonly_forced()

        @readonly
        async def outer_function():
            nonlocal outer_value
            outer_value = is_readonly_forced()
            await inner_function()

        await outer_function()

        assert outer_value is True
        assert inner_value is True
        assert is_readonly_forced() is False
