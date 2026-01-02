"""
Workflow Input File Database Model

Stores uploaded input files for workflows (Excel templates, data files, etc.)
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, BigInteger, Text, Boolean
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType


class WorkflowInputFile(Base):
    """Input files associated with workflows (templates, data sources, etc.)."""

    __tablename__ = "workflow_input_files"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    workflow_id = Column(
        BigIntegerType,
        ForeignKey("workflows.id", ondelete="CASCADE"),
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
    name = Column(String(255), nullable=False)  # Original filename
    description = Column(Text, nullable=True)
    storage_path = Column(String(500), nullable=False)  # Full GCS path
    file_size = Column(BigInteger, nullable=False)  # Bytes
    mime_type = Column(String(100), nullable=True)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted = Column(Boolean, nullable=False, default=False, server_default="false")
