from sqlalchemy import Column, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from common.db.base import Base, BigIntegerType


class AnswerEntity(Base):
    __tablename__ = "answers"

    id = Column(BigIntegerType, primary_key=True, index=True)
    answer_set_id = Column(BigIntegerType, ForeignKey("answer_sets.id"), nullable=False)
    company_id = Column(
        BigIntegerType, ForeignKey("companies.id"), nullable=False, index=True
    )
    answer_data = Column(JSON, nullable=False)
    current_citation_set_id = Column(
        BigIntegerType, ForeignKey("citation_sets.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    # answer_set = relationship("AnswerSetEntity", back_populates="answers")
    ## All citation sets for this answer (one-to-many, but we use one-to-one in practice)
    # citation_sets = relationship(
    #    "CitationSetEntity",
    #    back_populates="answer",
    #    foreign_keys="CitationSetEntity.answer_id",
    # )
    ## The current active citation set
    # current_citation_set = relationship(
    #    "CitationSetEntity",
    #    foreign_keys=[current_citation_set_id],
    #    uselist=False,
    #    post_update=True,
    # )
