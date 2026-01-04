"""
Service for managing workflow execution files.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from packages.workflows.repositories.execution_file_repository import (
    ExecutionFileRepository,
)
from packages.workflows.models.domain.execution_file import (
    ExecutionFileCreateModel,
    ExecutionFileModel,
)
from packages.workflows.models.database.execution_file import ExecutionFileType
from packages.workflows.services.workflow_storage_service import WorkflowStorageService
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class ExecutionFileService:
    """Service for execution file operations."""

    def __init__(self):
        self.repository = ExecutionFileRepository()
        self.storage_service = WorkflowStorageService()

    @trace_span
    async def create_file_record(
        self, file_data: ExecutionFileCreateModel
    ) -> ExecutionFileModel:
        """Create a new execution file record."""
        return await self.repository.create(file_data)

    @trace_span
    async def get_file(
        self, file_id: int, company_id: int
    ) -> Optional[ExecutionFileModel]:
        """Get an execution file by ID with company filtering."""
        file = await self.repository.get(file_id)
        if file and file.company_id != company_id:
            return None
        return file

    @trace_span
    async def list_execution_files(
        self,
        execution_id: int,
        company_id: int,
        file_type: ExecutionFileType | None = None,
    ) -> List[ExecutionFileModel]:
        """List files for an execution with company filtering."""
        files = await self.repository.list_by_execution(execution_id, file_type)
        # Filter by company_id for security
        return [f for f in files if f.company_id == company_id]

    @trace_span
    async def download_file(
        self, file_id: int, execution_id: int, company_id: int
    ) -> tuple[bytes, ExecutionFileModel]:
        """
        Download an execution file.

        Args:
            file_id: File ID
            execution_id: Execution ID (for security check)
            company_id: Company ID (for security check)

        Returns:
            Tuple of (file_data, file_metadata)
        """
        file = await self.repository.get(file_id)
        if (
            not file
            or file.execution_id != execution_id
            or file.company_id != company_id
        ):
            raise ValueError(f"File {file_id} not found for execution {execution_id}")

        file_data = await self.storage_service.download_file(file.storage_path)
        return file_data, file
