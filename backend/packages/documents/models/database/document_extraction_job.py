from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobStatus,
)


class DocumentExtractionJobEntity(Base):
    __tablename__ = "document_extraction_jobs"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    document_id = Column(
        BigIntegerType, ForeignKey("documents.id"), nullable=False, index=True
    )
    status = Column(
        String,
        default=DocumentExtractionJobStatus.QUEUED.value,
        nullable=False,
        index=True,
    )
    worker_message_id = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    extracted_content_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # document = relationship("DocumentEntity", backref="extraction_jobs")
