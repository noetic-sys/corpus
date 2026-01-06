"""
Child workflow for converting a single PDF page to markdown using Gemini.
Much simpler than Datalab since Gemini is synchronous.
"""

from temporalio import workflow
from datetime import timedelta

from .common import (
    MarkdownPage,
    CONVERT_PAGE_TO_MARKDOWN_ACTIVITY,
)


@workflow.defn
class ConvertPageWorkflow:
    @workflow.run
    async def run(
        self, page_url: str, page_number: int, trace_headers: dict = None
    ) -> MarkdownPage:
        """
        Child workflow that converts a single PDF page to markdown using Gemini.
        No polling needed since Gemini extraction is synchronous!
        """
        workflow.logger.info(
            f"Starting page conversion workflow for page {page_number}"
        )

        # Convert page directly using Gemini (synchronous)
        markdown_content = await workflow.execute_activity(
            CONVERT_PAGE_TO_MARKDOWN_ACTIVITY,
            args=[page_url, trace_headers],
            start_to_close_timeout=timedelta(
                minutes=5
            ),  # Longer timeout for Gemini processing
        )

        workflow.logger.info(f"Page {page_number} conversion completed")
        return MarkdownPage(page_number=page_number, content=markdown_content)
