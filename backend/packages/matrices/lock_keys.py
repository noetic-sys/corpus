"""Lock key generators for matrices package."""


# Lock TTL for matrix structural operations (seconds) - safety net if process crashes
MATRIX_STRUCTURE_LOCK_TTL = 30

# Max time to wait acquiring the lock before failing (seconds)
MATRIX_STRUCTURE_LOCK_ACQUIRE_TIMEOUT = 5.0


def matrix_structure_lock_key(matrix_id: int) -> str:
    """Generate lock key for matrix structural operations.

    This lock prevents race conditions when multiple requests try to
    modify the same matrix structure concurrently (e.g., adding documents
    in parallel to a cross-correlation matrix).
    """
    return f"matrix_structure:{matrix_id}"
