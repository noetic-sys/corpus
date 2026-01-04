import pytest
from packages.workflows.models.domain.execution_file import (
    ExecutionFileCreateModel,
)
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from packages.workflows.services.execution_file_service import ExecutionFileService
from packages.workflows.models.database.execution_file import (
    WorkflowExecutionFile,
    ExecutionFileType,
)


class TestExecutionFileService:
    """Test ExecutionFileService methods."""

    @pytest.fixture
    def mock_storage_service(self):
        """Create mock storage service."""
        mock = AsyncMock()
        mock.download_file = AsyncMock(return_value=b"test file data")
        return mock

    @pytest.fixture
    async def service(self, test_db: AsyncSession, mock_storage_service):
        """Create service instance with mocked storage."""
        with patch(
            "packages.workflows.services.execution_file_service.WorkflowStorageService",
            return_value=mock_storage_service,
        ):
            return ExecutionFileService()

    async def test_create_file_record(
        self, service, sample_workflow_execution, sample_company
    ):
        """Test creating a file record."""

        file_data = ExecutionFileCreateModel(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type="output",
            name="report.pdf",
            storage_path="workflows/executions/1/outputs/report.pdf",
            file_size=8192,
            mime_type="application/pdf",
        )

        result = await service.create_file_record(file_data)

        assert result is not None
        assert result.name == "report.pdf"
        assert result.execution_id == sample_workflow_execution.id
        assert result.company_id == sample_company.id

    async def test_get_file(
        self, service, sample_workflow_execution_file, sample_company
    ):
        """Test getting a file by ID."""
        result = await service.get_file(
            sample_workflow_execution_file.id, sample_company.id
        )

        assert result is not None
        assert result.id == sample_workflow_execution_file.id
        assert result.company_id == sample_company.id

    async def test_get_file_wrong_company(
        self, service, sample_workflow_execution_file, second_company
    ):
        """Test getting file with wrong company ID returns None."""
        result = await service.get_file(
            sample_workflow_execution_file.id, second_company.id
        )

        assert result is None

    async def test_list_execution_files(
        self, service, sample_workflow_execution, sample_company, test_db
    ):
        """Test listing files for an execution."""
        # Create multiple files
        file1 = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.OUTPUT.value,
            name="output1.xlsx",
            storage_path="workflows/executions/1/outputs/output1.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        file2 = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.SCRATCH.value,
            name="debug.txt",
            storage_path="workflows/executions/1/scratch/debug.txt",
            file_size=512,
            mime_type="text/plain",
        )
        test_db.add_all([file1, file2])
        await test_db.commit()

        results = await service.list_execution_files(
            sample_workflow_execution.id, sample_company.id
        )

        assert len(results) == 2

    async def test_list_execution_files_filtered_by_type(
        self, service, sample_workflow_execution, sample_company, test_db
    ):
        """Test listing files filtered by type."""
        # Create files of different types
        file1 = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.OUTPUT.value,
            name="output.xlsx",
            storage_path="workflows/executions/1/outputs/output.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        file2 = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.SCRATCH.value,
            name="debug.txt",
            storage_path="workflows/executions/1/scratch/debug.txt",
            file_size=512,
            mime_type="text/plain",
        )
        test_db.add_all([file1, file2])
        await test_db.commit()

        # Get only output files
        results = await service.list_execution_files(
            sample_workflow_execution.id,
            sample_company.id,
            file_type=ExecutionFileType.OUTPUT,
        )

        assert len(results) == 1
        assert results[0].file_type == ExecutionFileType.OUTPUT

    async def test_list_execution_files_wrong_company(
        self,
        service,
        sample_workflow_execution,
        sample_company,
        second_company,
        test_db,
    ):
        """Test listing files with wrong company returns empty."""
        # Create file for first company
        file1 = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.OUTPUT.value,
            name="output.xlsx",
            storage_path="workflows/executions/1/outputs/output.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        test_db.add(file1)
        await test_db.commit()

        # Try to list with different company
        results = await service.list_execution_files(
            sample_workflow_execution.id, second_company.id
        )

        assert len(results) == 0

    async def test_download_file(
        self,
        service,
        sample_workflow_execution_file,
        sample_company,
        mock_storage_service,
    ):
        """Test downloading a file."""
        file_data, file_metadata = await service.download_file(
            sample_workflow_execution_file.id,
            sample_workflow_execution_file.execution_id,
            sample_company.id,
        )

        assert file_data == b"test file data"
        assert file_metadata.id == sample_workflow_execution_file.id
        mock_storage_service.download_file.assert_called_once()

    async def test_download_file_wrong_execution(
        self, service, sample_workflow_execution_file, sample_company
    ):
        """Test downloading file with wrong execution ID raises error."""
        with pytest.raises(ValueError, match="not found for execution"):
            await service.download_file(
                sample_workflow_execution_file.id,
                999,  # Wrong execution ID
                sample_company.id,
            )

    async def test_download_file_wrong_company(
        self, service, sample_workflow_execution_file, second_company
    ):
        """Test downloading file with wrong company ID raises error."""
        with pytest.raises(ValueError, match="not found for execution"):
            await service.download_file(
                sample_workflow_execution_file.id,
                sample_workflow_execution_file.execution_id,
                second_company.id,  # Wrong company
            )

    async def test_download_nonexistent_file(
        self, service, sample_workflow_execution, sample_company
    ):
        """Test downloading nonexistent file raises error."""
        with pytest.raises(ValueError, match="not found for execution"):
            await service.download_file(
                999,  # Nonexistent file ID
                sample_workflow_execution.id,
                sample_company.id,
            )
