import pytest
from unittest.mock import AsyncMock, patch
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession
from packages.workflows.services.input_file_service import InputFileService


class TestInputFileService:
    """Test InputFileService methods."""

    @pytest.fixture
    def mock_storage_service(self):
        """Create mock storage service."""
        mock = AsyncMock()
        mock.upload_template = AsyncMock(
            return_value=("companies/1/workflows/1/templates/abc123_test.txt", "abc123")
        )
        mock.download_file = AsyncMock(return_value=b"test file data")
        return mock

    @pytest.fixture
    async def service(self, test_db: AsyncSession, mock_storage_service):
        """Create service instance with mocked storage."""
        with patch(
            "packages.workflows.services.input_file_service.WorkflowStorageService",
            return_value=mock_storage_service,
        ):
            return InputFileService(test_db)

    async def test_upload_file(
        self, service, sample_workflow, sample_company, mock_storage_service
    ):
        """Test uploading a workflow input file."""
        file_data = BytesIO(b"test file content")

        result = await service.upload_file(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            filename="test.txt",
            file_data=file_data,
            file_size=17,
            description="Test file",
            content_type="text/plain",
        )

        assert result is not None
        assert result.name == "test.txt"
        assert result.workflow_id == sample_workflow.id
        assert result.company_id == sample_company.id
        assert (
            result.storage_path == "companies/1/workflows/1/templates/abc123_test.txt"
        )
        assert result.file_size == 17
        mock_storage_service.upload_template.assert_called_once()

    async def test_upload_file_nonexistent_workflow(
        self, service, sample_company, mock_storage_service
    ):
        """Test uploading file for nonexistent workflow raises error."""
        file_data = BytesIO(b"test file content")

        with pytest.raises(Exception, match="not found"):
            await service.upload_file(
                workflow_id=999,
                company_id=sample_company.id,
                filename="test.txt",
                file_data=file_data,
                file_size=17,
            )

    async def test_upload_file_wrong_company(
        self, service, sample_workflow, second_company, mock_storage_service
    ):
        """Test uploading file with wrong company ID raises error."""
        file_data = BytesIO(b"test file content")

        with pytest.raises(Exception, match="not found"):
            await service.upload_file(
                workflow_id=sample_workflow.id,
                company_id=second_company.id,
                filename="test.txt",
                file_data=file_data,
                file_size=17,
            )

    async def test_list_files(
        self, service, sample_workflow, sample_company, sample_workflow_input_file
    ):
        """Test listing input files for a workflow."""
        files = await service.list_files(sample_workflow.id, sample_company.id)

        assert len(files) == 1
        assert files[0].id == sample_workflow_input_file.id

    async def test_list_files_wrong_company(
        self, service, sample_workflow, second_company
    ):
        """Test listing files with wrong company raises error."""
        with pytest.raises(Exception, match="not found"):
            await service.list_files(sample_workflow.id, second_company.id)

    async def test_download_file(
        self, service, sample_workflow_input_file, sample_company, mock_storage_service
    ):
        """Test downloading an input file."""
        file_data, file_metadata = await service.download_file(
            sample_workflow_input_file.id, sample_company.id
        )

        assert file_data == b"test file data"
        assert file_metadata.id == sample_workflow_input_file.id
        mock_storage_service.download_file.assert_called_once()

    async def test_download_file_wrong_company(
        self, service, sample_workflow_input_file, second_company
    ):
        """Test downloading file with wrong company raises error."""
        with pytest.raises(ValueError, match="not found"):
            await service.download_file(
                sample_workflow_input_file.id, second_company.id
            )

    async def test_delete_file(
        self, service, sample_workflow_input_file, sample_company
    ):
        """Test soft deleting an input file."""
        success = await service.delete_file(
            sample_workflow_input_file.id, sample_company.id
        )

        assert success is True

    async def test_delete_file_wrong_company(
        self, service, sample_workflow_input_file, second_company
    ):
        """Test deleting file with wrong company raises error."""
        with pytest.raises(ValueError, match="not found"):
            await service.delete_file(sample_workflow_input_file.id, second_company.id)
