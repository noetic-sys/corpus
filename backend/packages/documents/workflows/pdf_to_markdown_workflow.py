"""
Main PDF to Markdown workflow.
Orchestrates the complete PDF extraction process.
"""

from temporalio import workflow
from datetime import timedelta
import asyncio
import logging

from .common import (
    PDFProcessingInput,
    TaskQueueType,
    SPLIT_PDF_ACTIVITY,
    COMBINE_MARKDOWN_ACTIVITY,
    SAVE_MARKDOWN_TO_S3_ACTIVITY,
    INDEX_DOCUMENT_FOR_SEARCH_ACTIVITY,
)
from .convert_page_workflow import ConvertPageWorkflow

logger = logging.getLogger(__name__)


@workflow.defn
class PDFToMarkdownWorkflow:
    @workflow.run
    async def run(self, input_data: PDFProcessingInput) -> dict:
        """
        PDF-specific workflow that:
        1. Downloads and splits PDF into pages
        2. Launches child workflows to convert each page to markdown
        3. Combines all markdown content in order
        4. Returns S3 key (status updates handled by parent workflow)
        """
        logger.info(
            f"Starting PDF to Markdown workflow for document {input_data.document_id}"
        )

        # Step 1: Split PDF into pages
        page_urls = await workflow.execute_activity(
            SPLIT_PDF_ACTIVITY,
            args=[input_data.document_id, input_data.trace_headers],
            start_to_close_timeout=timedelta(minutes=10),
        )

        logger.info(f"PDF split into {len(page_urls)} pages")

        # Step 2: Convert each page to markdown in parallel using child workflows
        child_workflow_tasks = []
        for i, page_url in enumerate(page_urls):
            task = workflow.execute_child_workflow(
                ConvertPageWorkflow.run,
                args=[page_url, i, input_data.trace_headers],
                id=f"convert-page-{input_data.document_id}-{i}",
                task_queue=TaskQueueType.PAGE_CONVERSION.value,
            )
            child_workflow_tasks.append(task)

        # Step 3: Wait for all page conversions to complete
        markdown_pages = await asyncio.gather(*child_workflow_tasks)

        # Sort by page number (in case they complete out of order)
        markdown_pages.sort(key=lambda x: x.page_number)

        logger.info(f"All {len(markdown_pages)} pages converted successfully")

        # Step 4: Combine all markdown content
        combined_markdown = await workflow.execute_activity(
            COMBINE_MARKDOWN_ACTIVITY,
            args=[markdown_pages, input_data.trace_headers],
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Step 5: Save combined markdown to S3
        s3_key = await workflow.execute_activity(
            SAVE_MARKDOWN_TO_S3_ACTIVITY,
            args=[
                combined_markdown,
                input_data.document_id,
                input_data.trace_headers,
            ],
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Step 6: Index document for search with extracted content
        await workflow.execute_activity(
            INDEX_DOCUMENT_FOR_SEARCH_ACTIVITY,
            args=[
                input_data.document_id,
                combined_markdown,
                input_data.trace_headers,
            ],
            start_to_close_timeout=timedelta(minutes=2),
            # retry_policy=workflow.RetryPolicy(
            #    initial_interval=timedelta(seconds=1),
            #    maximum_interval=timedelta(seconds=30),
            #    maximum_attempts=3,
            #    non_retryable_error_types=[]
            # ),
        )

        logger.info(
            f"PDF to Markdown workflow completed successfully for document {input_data.document_id}"
        )
        return {"s3_key": s3_key, "char_count": len(combined_markdown)}
