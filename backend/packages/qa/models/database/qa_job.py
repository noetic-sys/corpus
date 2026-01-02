from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func

from common.db.base import Base, BigIntegerType
from packages.qa.models.domain.qa_job import QAJobStatus


class QAJobEntity(Base):
    __tablename__ = "qa_jobs"

    id = Column(BigIntegerType, primary_key=True, index=True, autoincrement=True)
    matrix_cell_id = Column(
        BigIntegerType, ForeignKey("matrix_cells.id"), nullable=False
    )
    status = Column(String, default=QAJobStatus.QUEUED.value, nullable=False)
    worker_message_id = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # matrix_cell = relationship("MatrixCellEntity", back_populates="qa_jobs")
