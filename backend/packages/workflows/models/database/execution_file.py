"""
Workflow Execution File Database Model

Tracks files generated during workflow execution (outputs and scratch files)
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, BigInteger
from sqlalchemy.sql import func
from enum import StrEnum

from common.db.base import Base, BigIntegerType


class ExecutionFileType(StrEnum):
    """Type of execution file."""

    OUTPUT = "output"  # Final deliverable
    SCRATCH = "scratch"  # Working/debug file


class WorkflowExecutionFile(Base):
    """Files generated during workflow execution."""

    __tablename__ = "workflow_execution_files"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    execution_id = Column(
        BigIntegerType,
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        BigIntegerType,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File metadata
    file_type = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Filename
    storage_path = Column(String(500), nullable=False)  # Full GCS path
    file_size = Column(BigInteger, nullable=False)  # Bytes
    mime_type = Column(String(100), nullable=True)

    # Audit
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
