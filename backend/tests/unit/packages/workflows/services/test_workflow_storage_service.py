import pytest
from unittest.mock import AsyncMock, patch
from io import BytesIO
from packages.workflows.services.workflow_storage_service import WorkflowStorageService


class TestWorkflowStorageService:
    """Test WorkflowStorageService methods."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage provider."""
        mock = AsyncMock()
        mock.upload = AsyncMock(return_value=True)
        mock.download = AsyncMock(return_value=b"test file data")
        mock.delete = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def service(self, mock_storage):
        """Create service instance with mocked storage."""
        with patch(
            "packages.workflows.services.workflow_storage_service.get_storage",
            return_value=mock_storage,
        ):
            return WorkflowStorageService()

    def test_calculate_hash(self, service):
        """Test hash calculation."""
        file_data = BytesIO(b"test content")
        hash_result = service._calculate_hash(file_data)

        assert hash_result is not None
        assert len(hash_result) == 64  # SHA256 hex digest is 64 chars
        assert file_data.tell() == 0  # File pointer should be reset

    def test_calculate_hash_consistent(self, service):
        """Test hash calculation is consistent."""
        content = b"test content"
        file_data1 = BytesIO(content)
        file_data2 = BytesIO(content)

        hash1 = service._calculate_hash(file_data1)
        hash2 = service._calculate_hash(file_data2)

        assert hash1 == hash2

    def test_get_template_path(self, service):
        """Test template path generation with hash."""
        path = service._get_template_path(
            company_id=1, workflow_id=5, file_hash="abc123", filename="template.xlsx"
        )

        assert path == "companies/1/workflows/5/templates/abc123_template.xlsx"

    def test_get_execution_output_path(self, service):
        """Test execution output path generation."""
        path = service._get_execution_output_path(
            company_id=1, workflow_id=5, execution_id=10, filename="output.pdf"
        )

        assert path == "companies/1/workflows/5/executions/10/outputs/output.pdf"

    def test_get_execution_scratch_path(self, service):
        """Test execution scratch path generation."""
        path = service._get_execution_scratch_path(
            company_id=1, workflow_id=5, execution_id=10, filename="temp.json"
        )

        assert path == "companies/1/workflows/5/executions/10/scratch/temp.json"

    async def test_upload_template(self, service, mock_storage):
        """Test uploading a template file."""
        file_data = BytesIO(b"test template content")

        storage_path, file_hash = await service.upload_template(
            company_id=1,
            workflow_id=5,
            filename="template.xlsx",
            file_data=file_data,
            file_size=100,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        assert storage_path.startswith("companies/1/workflows/5/templates/")
        assert "template.xlsx" in storage_path
        assert file_hash is not None
        assert len(file_hash) == 64
        mock_storage.upload.assert_called_once()

    async def test_upload_template_auto_content_type(self, service, mock_storage):
        """Test uploading template with auto-detected content type."""
        file_data = BytesIO(b"test content")

        storage_path, file_hash = await service.upload_template(
            company_id=1,
            workflow_id=5,
            filename="data.csv",
            file_data=file_data,
            file_size=100,
        )

        assert storage_path is not None
        assert file_hash is not None
        # Check that upload was called with text/csv content type
        call_args = mock_storage.upload.call_args
        assert call_args[0][2]["content_type"] == "text/csv"

    async def test_upload_template_upload_fails(self, service, mock_storage):
        """Test upload failure raises exception."""
        mock_storage.upload.return_value = False
        file_data = BytesIO(b"test content")

        with pytest.raises(Exception, match="Failed to upload template file"):
            await service.upload_template(
                company_id=1,
                workflow_id=5,
                filename="test.txt",
                file_data=file_data,
                file_size=100,
            )

    async def test_upload_execution_output(self, service, mock_storage):
        """Test uploading execution output file."""
        file_data = BytesIO(b"output data")

        storage_path = await service.upload_execution_output(
            company_id=1,
            workflow_id=5,
            execution_id=10,
            filename="report.pdf",
            file_data=file_data,
            content_type="application/pdf",
        )

        assert (
            storage_path == "companies/1/workflows/5/executions/10/outputs/report.pdf"
        )
        mock_storage.upload.assert_called_once()

    async def test_upload_execution_scratch(self, service, mock_storage):
        """Test uploading execution scratch file."""
        file_data = BytesIO(b"scratch data")

        storage_path = await service.upload_execution_scratch(
            company_id=1,
            workflow_id=5,
            execution_id=10,
            filename="temp.json",
            file_data=file_data,
            content_type="application/json",
        )

        assert storage_path == "companies/1/workflows/5/executions/10/scratch/temp.json"
        mock_storage.upload.assert_called_once()

    async def test_download_file(self, service, mock_storage):
        """Test downloading a file."""
        content = await service.download_file(
            "companies/1/workflows/5/templates/abc_test.txt"
        )

        assert content == b"test file data"
        mock_storage.download.assert_called_once_with(
            "companies/1/workflows/5/templates/abc_test.txt"
        )

    async def test_download_file_not_found(self, service, mock_storage):
        """Test downloading nonexistent file raises error."""
        mock_storage.download.return_value = None

        with pytest.raises(Exception, match="File not found"):
            await service.download_file("companies/1/workflows/5/templates/missing.txt")

    async def test_generate_signed_url(self, service):
        """Test generating signed URL (placeholder implementation)."""
        url = await service.generate_signed_url(
            "companies/1/workflows/5/templates/abc_test.txt", expiration_seconds=7200
        )

        assert url is not None
        assert "companies/1/workflows/5/templates/abc_test.txt" in url
        assert "expires=7200" in url

    async def test_delete_file(self, service, mock_storage):
        """Test deleting a file."""
        await service.delete_file("companies/1/workflows/5/templates/abc_test.txt")

        mock_storage.delete.assert_called_once_with(
            "companies/1/workflows/5/templates/abc_test.txt"
        )

    async def test_list_execution_files(self, service):
        """Test listing execution files (placeholder implementation)."""
        files = await service.list_execution_files(
            company_id=1, execution_id=10, file_type="outputs"
        )

        assert files == []  # Placeholder returns empty list
