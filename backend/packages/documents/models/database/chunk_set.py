from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from common.db.base import Base, BigIntegerType


class ChunkSetEntity(Base):
    __tablename__ = "chunk_sets"

    id = Column(BigIntegerType, primary_key=True, index=True)
    document_id = Column(
        BigIntegerType, ForeignKey("documents.id"), nullable=False, index=True
    )
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    chunking_strategy = Column(
        String, nullable=False
    )  # e.g., "agent_v1", "fixed_size_512"
    total_chunks = Column(Integer, nullable=False, default=0)
    s3_prefix = Column(String, nullable=False)  # S3 prefix where chunks are stored
    deleted = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # document = relationship("DocumentEntity", back_populates="chunk_sets")
    # chunks = relationship(
    #     "ChunkEntity", back_populates="chunk_set", cascade="all, delete-orphan"
    # )
