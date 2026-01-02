from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class UserEntity(Base):
    __tablename__ = "users"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    email = Column(String, nullable=False, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # Optional for SSO-only users
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)  # Company admin
    sso_provider = Column(String, nullable=True)  # SSOProvider enum value
    sso_user_id = Column(String, nullable=True, index=True)  # External SSO user ID
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # company = relationship("CompanyEntity", back_populates="users")
