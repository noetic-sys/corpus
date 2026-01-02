from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from common.db.base import Base, BigIntegerType


class CitationSetEntity(Base):
    __tablename__ = "citation_sets"

    id = Column(BigIntegerType, primary_key=True, index=True)
    answer_id = Column(BigIntegerType, ForeignKey("answers.id"), nullable=False)
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # answer = relationship(
    #    "AnswerEntity", back_populates="citation_sets", foreign_keys=[answer_id]
    # )
    # citations = relationship(
    #    "CitationEntity", back_populates="citation_set", cascade="all, delete-orphan"
    # )


class CitationEntity(Base):
    __tablename__ = "citations"

    id = Column(BigIntegerType, primary_key=True, index=True)
    citation_set_id = Column(
        BigIntegerType, ForeignKey("citation_sets.id"), nullable=False
    )
    document_id = Column(BigIntegerType, ForeignKey("documents.id"), nullable=False)
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    quote_text = Column(
        Text, nullable=False
    )  # Exact text from document for highlighting
    citation_order = Column(
        Integer, nullable=False
    )  # For [[cite:1]], [[cite:2]] ordering
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # citation_set = relationship("CitationSetEntity", back_populates="citations")
    # document = relationship("DocumentEntity")
