"""Cache key generators for users package repositories."""


def user_by_sso_key(sso_provider: str, sso_user_id: str) -> str:
    """Generate cache key for user by SSO provider and user ID."""
    return f"sso:{sso_provider}:{sso_user_id}:user"
