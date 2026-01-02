from fastapi import APIRouter, Depends
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.users.models.schemas.protected import ProtectedResponse, ProfileResponse

router = APIRouter()


@router.get("/protected", response_model=ProtectedResponse)
async def protected_route(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Example protected route that requires authentication."""
    return ProtectedResponse(
        message="Hello authenticated user!",
        user_id=current_user.id,
        email=current_user.email,
        company_id=current_user.company_id,
        is_admin=current_user.is_admin,
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get current user profile."""
    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        company_id=current_user.company_id,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )
