from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean,
    BigInteger,
    JSON,
)
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class WorkflowEntity(Base):
    __tablename__ = "workflows"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Triggering
    trigger_type = Column(String(50), nullable=False, index=True)

    # Source workspace
    workspace_id = Column(
        BigIntegerType, ForeignKey("workspaces.id"), nullable=False, index=True
    )

    # Output
    output_type = Column(String(50), nullable=False)

    # State
    deleted = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkflowExecutionEntity(Base):
    __tablename__ = "workflow_executions"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    workflow_id = Column(
        BigIntegerType, ForeignKey("workflows.id"), nullable=False, index=True
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )

    # Execution details
    trigger_type = Column(String(50), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    status = Column(String(50), nullable=False, index=True)
    output_size_bytes = Column(BigInteger, nullable=True)

    # Debugging
    error_message = Column(Text, nullable=True)
    execution_log = Column(JSON, nullable=True)

    # Soft delete
    deleted = Column(Boolean, nullable=False, default=False, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
