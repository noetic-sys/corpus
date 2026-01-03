from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType
from packages.documents.models.domain.document import ExtractionStatus


class DocumentEntity(Base):
    __tablename__ = "documents"
    __table_args__ = (
        # Partial unique constraint: (company_id, checksum) where not deleted
        # Allows same document in different companies and re-upload after deletion
        Index(
            "uq_documents_company_checksum_not_deleted",
            "company_id",
            "checksum",
            unique=True,
            postgresql_where=Column("deleted") == False,
        ),
    )

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False, index=True)
    content_type = Column(String, nullable=True)
    file_size = Column(BigIntegerType, nullable=True)
    checksum = Column(
        String, nullable=False, index=True
    )  # Removed unique=True - now handled by __table_args__
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    # Extraction fields
    extracted_content_path = Column(String, nullable=True, index=True)
    extraction_status = Column(
        String, nullable=False, default=ExtractionStatus.PENDING.value, index=True
    )
    extraction_started_at = Column(DateTime(timezone=True), nullable=True)
    extraction_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Chunking preference
    use_agentic_chunking = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # indexing_jobs = relationship(
    #    "DocumentIndexingJobEntity",
    #    back_populates="document",
    #    cascade="all, delete-orphan",
    #    lazy="select",
    # )
