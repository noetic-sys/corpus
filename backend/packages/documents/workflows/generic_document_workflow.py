"""
Generic document extraction workflow for non-PDF files.
Handles Word, Excel, PowerPoint, images, text files, etc.
"""

from temporalio import workflow
from datetime import timedelta
import logging

from .common import (
    DocumentProcessingInput,
    EXTRACT_DOCUMENT_CONTENT_ACTIVITY,
    SAVE_EXTRACTED_CONTENT_TO_S3_ACTIVITY,
    INDEX_DOCUMENT_FOR_SEARCH_ACTIVITY,
    GET_DOCUMENT_DETAILS_ACTIVITY,
)

logger = logging.getLogger(__name__)


@workflow.defn
class GenericDocumentWorkflow:
    @workflow.run
    async def run(self, input_data: DocumentProcessingInput) -> str:
        """
        Generic workflow for extracting content from non-PDF documents.
        Much simpler than PDF workflow since no page splitting is needed.
        """
        logger.info(
            f"Starting generic document extraction for document {input_data.document_id}"
        )

        # Step 1: Get document details to retrieve company_id
        document_details = await workflow.execute_activity(
            GET_DOCUMENT_DETAILS_ACTIVITY,
            args=[input_data.document_id, input_data.trace_headers],
            start_to_close_timeout=timedelta(seconds=30),
        )
        company_id = document_details["company_id"]

        # Step 2: Extract content using appropriate extractor
        extracted_content = await workflow.execute_activity(
            EXTRACT_DOCUMENT_CONTENT_ACTIVITY,
            args=[
                input_data.document_id,
                input_data.trace_headers,
            ],
            start_to_close_timeout=timedelta(
                minutes=10
            ),  # Generous timeout for large files
        )

        logger.info(
            f"Extracted {len(extracted_content)} characters from document {input_data.document_id}"
        )

        # Step 3: Save extracted content to S3
        s3_key = await workflow.execute_activity(
            SAVE_EXTRACTED_CONTENT_TO_S3_ACTIVITY,
            args=[
                extracted_content,
                input_data.document_id,
                input_data.trace_headers,
            ],
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Step 4: Index document for search with extracted content
        await workflow.execute_activity(
            INDEX_DOCUMENT_FOR_SEARCH_ACTIVITY,
            args=[
                input_data.document_id,
                extracted_content,
                input_data.trace_headers,
            ],
            start_to_close_timeout=timedelta(minutes=2),
        )

        logger.info(
            f"Generic document extraction completed for document {input_data.document_id}"
        )
        return s3_key
