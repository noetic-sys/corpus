from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType
from packages.documents.models.domain.document_indexing_job import (
    DocumentIndexingJobStatus,
)


class DocumentIndexingJobEntity(Base):
    __tablename__ = "document_indexing_jobs"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    document_id = Column(BigIntegerType, ForeignKey("documents.id"), nullable=False)
    status = Column(
        String, default=DocumentIndexingJobStatus.QUEUED.value, nullable=False
    )
    worker_message_id = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # document = relationship("DocumentEntity", back_populates="indexing_jobs")
