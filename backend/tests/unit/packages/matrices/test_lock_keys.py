"""Tests for matrices lock key generators."""

from packages.matrices.lock_keys import (
    matrix_structure_lock_key,
    MATRIX_STRUCTURE_LOCK_TTL,
    MATRIX_STRUCTURE_LOCK_ACQUIRE_TIMEOUT,
)


class TestMatrixLockKeys:
    """Tests for matrix lock key generators."""

    def test_matrix_structure_lock_key_format(self):
        """Test lock key format is correct."""
        key = matrix_structure_lock_key(123)
        assert key == "matrix_structure:123"

    def test_matrix_structure_lock_key_different_ids(self):
        """Test different matrix IDs produce different keys."""
        key1 = matrix_structure_lock_key(1)
        key2 = matrix_structure_lock_key(2)
        assert key1 != key2
        assert key1 == "matrix_structure:1"
        assert key2 == "matrix_structure:2"

    def test_lock_ttl_is_reasonable(self):
        """Test lock TTL is a reasonable value."""
        assert MATRIX_STRUCTURE_LOCK_TTL > 0
        assert MATRIX_STRUCTURE_LOCK_TTL <= 60  # Should not be too long

    def test_acquire_timeout_is_reasonable(self):
        """Test acquire timeout is a reasonable value."""
        assert MATRIX_STRUCTURE_LOCK_ACQUIRE_TIMEOUT > 0
        assert MATRIX_STRUCTURE_LOCK_ACQUIRE_TIMEOUT <= 30  # Should not wait too long
