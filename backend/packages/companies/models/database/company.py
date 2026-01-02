from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class CompanyEntity(Base):
    __tablename__ = "companies"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    domain = Column(
        String, nullable=True, index=True, unique=True
    )  # for SSO domain mapping
    description = Column(Text, nullable=True)

    # Stripe customer ID - stored on company since it represents company identity
    stripe_customer_id = Column(String(255), nullable=True, unique=True, index=True)

    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # users = relationship(
    #    "UserEntity",
    #    back_populates="company",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
