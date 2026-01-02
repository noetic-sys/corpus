from pydantic import BaseModel


class QAJobMessage(BaseModel):
    """Message model for QA job processing.

    The worker will load entity references from the cell to determine
    which documents and questions to process based on cell type.
    """

    job_id: int
    matrix_cell_id: int


class DocumentExtractionMessage(BaseModel):
    """Message model for document extraction processing."""

    job_id: int
    document_id: int


class DocumentIndexingMessage(BaseModel):
    """Message model for document indexing processing."""

    job_id: int
    document_id: int
