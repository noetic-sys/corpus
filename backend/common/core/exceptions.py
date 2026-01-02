class AppException(Exception):
    """Base application exception."""

    pass


class NotFoundError(AppException):
    """Resource not found exception."""

    pass


class ValidationError(AppException):
    """Validation error exception."""

    pass


class StorageError(AppException):
    """Storage operation error exception."""

    pass


class ProcessingError(AppException):
    """Processing error exception."""

    pass
