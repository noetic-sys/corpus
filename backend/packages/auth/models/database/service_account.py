from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class ServiceAccountEntity(Base):
    __tablename__ = "service_accounts"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    api_key_hash = Column(String, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
