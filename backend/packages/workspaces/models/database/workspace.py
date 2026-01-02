from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class WorkspaceEntity(Base):
    __tablename__ = "workspaces"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # matrices = relationship(
    #    "MatrixEntity",
    #    back_populates="workspace",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
