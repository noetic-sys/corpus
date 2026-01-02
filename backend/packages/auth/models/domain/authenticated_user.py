from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """User context passed through authentication dependencies"""

    user_id: int
    # email: EmailStr
    # full_name: Optional[str] = None
    company_id: int
    # is_active: bool = True
    # is_admin: bool = False

    class Config:
        from_attributes = True
