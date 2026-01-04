"""
Service for managing workflow input files (templates, data files).
"""

from typing import BinaryIO, List, Tuple
from fastapi import HTTPException

from packages.workflows.repositories.input_file_repository import InputFileRepository
from packages.workflows.repositories.workflow_repository import WorkflowRepository
from packages.workflows.services.workflow_storage_service import WorkflowStorageService
from packages.workflows.models.domain.input_file import (
    InputFileModel,
    InputFileCreateModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class InputFileService:
    """Service for managing workflow input files."""

    def __init__(self):
        self.input_file_repo = InputFileRepository()
        self.workflow_repo = WorkflowRepository()
        self.storage_service = WorkflowStorageService()

    @trace_span
    async def upload_file(
        self,
        workflow_id: int,
        company_id: int,
        filename: str,
        file_data: BinaryIO,
        file_size: int,
        description: str | None = None,
        content_type: str | None = None,
    ) -> InputFileModel:
        """
        Upload an input file for a workflow.

        Validates workflow access, uploads to storage, creates DB record.
        """
        logger.info(f"Uploading input file {filename} for workflow {workflow_id}")

        # Validate workflow exists and user has access
        workflow = await self.workflow_repo.get(workflow_id, company_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if workflow.company_id != company_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Upload to storage first (calculates hash internally)
        storage_path, file_hash = await self.storage_service.upload_template(
            company_id=company_id,
            workflow_id=workflow_id,
            filename=filename,
            file_data=file_data,
            file_size=file_size,
            content_type=content_type,
        )

        # Create DB record once with final values
        create_model = InputFileCreateModel(
            workflow_id=workflow_id,
            company_id=company_id,
            name=filename,
            description=description,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=content_type,
        )

        input_file = await self.input_file_repo.create(create_model)

        logger.info(
            f"Uploaded input file {input_file.id}: {filename} (hash: {file_hash})"
        )
        return input_file

    @trace_span
    async def list_files(
        self,
        workflow_id: int,
        company_id: int,
    ) -> List[InputFileModel]:
        """List all input files for a workflow."""
        # Validate workflow access
        workflow = await self.workflow_repo.get(workflow_id, company_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if workflow.company_id != company_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return await self.input_file_repo.list_by_workflow(workflow_id, company_id)

    @trace_span
    async def download_file(
        self,
        file_id: int,
        company_id: int,
    ) -> Tuple[bytes, InputFileModel]:
        """Download an input file."""
        file = await self.input_file_repo.get(file_id, company_id)
        if not file:
            raise ValueError("File not found")

        file_data = await self.storage_service.download_file(file.storage_path)
        return file_data, file

    @trace_span
    async def delete_file(
        self,
        file_id: int,
        company_id: int,
    ) -> bool:
        """Soft delete an input file (keeps storage, marks as deleted in DB)."""
        logger.info(f"Soft deleting input file {file_id}")

        file = await self.input_file_repo.get(file_id, company_id)
        if not file:
            raise ValueError("File not found")

        # Soft delete in DB (keeps S3 file)
        success = await self.input_file_repo.delete(file_id, company_id)

        logger.info(f"Soft deleted input file {file_id}")
        return success
