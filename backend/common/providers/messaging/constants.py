"""Constants for messaging system."""

from enum import StrEnum


class QueueName(StrEnum):
    """Queue names for the messaging system."""

    QA_WORKER = "qa_worker"
    DOCUMENT_EXTRACTOR = "document_extractor"
    DOCUMENT_EXTRACTION_WORKER = "document_extraction_worker"
    DOCUMENT_INDEXING = "document_indexing"
