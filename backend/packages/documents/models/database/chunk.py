from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from common.db.base import Base, BigIntegerType


class ChunkEntity(Base):
    __tablename__ = "chunks"

    id = Column(BigIntegerType, primary_key=True, index=True)
    chunk_set_id = Column(
        BigIntegerType, ForeignKey("chunk_sets.id"), nullable=False, index=True
    )
    chunk_id = Column(
        String, nullable=False, index=True
    )  # Original chunk_1, chunk_2 from agent
    document_id = Column(
        BigIntegerType, ForeignKey("documents.id"), nullable=False, index=True
    )  # Denormalized for queries
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    s3_key = Column(String, nullable=False)  # Actual content location in S3
    chunk_metadata = Column(JSON, nullable=False)  # page_start, page_end, section, etc.
    chunk_order = Column(Integer, nullable=False)  # Position in document
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # chunk_set = relationship("ChunkSetEntity", back_populates="chunks")
