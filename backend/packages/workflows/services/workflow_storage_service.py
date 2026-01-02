"""
Workflow Storage Service

Handles file uploads/downloads for workflows with company-scoped paths.
Separate from DocumentService - this handles workflow templates, execution outputs, and scratch files.
"""

from typing import BinaryIO, Optional
import mimetypes
import hashlib

from common.providers.storage.factory import get_storage


class WorkflowStorageService:
    """Service for managing workflow-related files in cloud storage."""

    def __init__(self):
        """Initialize storage service."""
        self.storage = get_storage()

    def _calculate_hash(self, file_data: BinaryIO) -> str:
        """Calculate SHA256 hash of file content."""
        sha256_hash = hashlib.sha256()
        chunk_size = 8192  # 8KB chunks

        # Read and hash file
        while chunk := file_data.read(chunk_size):
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            sha256_hash.update(chunk)

        # Reset file pointer
        file_data.seek(0)
        return sha256_hash.hexdigest()

    def _get_template_path(
        self, company_id: int, workflow_id: int, file_hash: str, filename: str
    ) -> str:
        """Generate storage path for workflow template file."""
        return f"companies/{company_id}/workflows/{workflow_id}/templates/{file_hash}_{filename}"

    def _get_execution_output_path(
        self, company_id: int, workflow_id: int, execution_id: int, filename: str
    ) -> str:
        """Generate storage path for execution output file."""
        return f"companies/{company_id}/workflows/{workflow_id}/executions/{execution_id}/outputs/{filename}"

    def _get_execution_scratch_path(
        self, company_id: int, workflow_id: int, execution_id: int, filename: str
    ) -> str:
        """Generate storage path for execution scratch file."""
        return f"companies/{company_id}/workflows/{workflow_id}/executions/{execution_id}/scratch/{filename}"

    def _get_execution_manifest_path(
        self, company_id: int, workflow_id: int, execution_id: int
    ) -> str:
        """Generate storage path for execution manifest file."""
        return f"companies/{company_id}/workflows/{workflow_id}/executions/{execution_id}/.manifest.json"

    async def upload_template(
        self,
        company_id: int,
        workflow_id: int,
        filename: str,
        file_data: BinaryIO,
        file_size: int,
        content_type: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Upload workflow template file.

        Args:
            company_id: Company ID for path scoping
            workflow_id: Workflow ID
            filename: Original filename
            file_data: File binary data
            file_size: File size in bytes
            content_type: MIME type (auto-detected if not provided)

        Returns:
            Tuple of (storage_path, file_hash)
        """
        # Calculate hash first
        file_hash = self._calculate_hash(file_data)

        storage_path = self._get_template_path(
            company_id, workflow_id, file_hash, filename
        )

        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)

        success = await self.storage.upload(
            storage_path,
            file_data,
            {"content_type": content_type or "application/octet-stream"},
        )

        if not success:
            raise Exception(f"Failed to upload template file {filename}")

        return storage_path, file_hash

    async def upload_execution_output(
        self,
        company_id: int,
        workflow_id: int,
        execution_id: int,
        filename: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload execution output file.

        Returns:
            Storage path
        """
        storage_path = self._get_execution_output_path(
            company_id, workflow_id, execution_id, filename
        )

        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)

        success = await self.storage.upload(
            storage_path,
            file_data,
            {"content_type": content_type or "application/octet-stream"},
        )

        if not success:
            raise Exception(f"Failed to upload output file {filename}")

        return storage_path

    async def upload_execution_scratch(
        self,
        company_id: int,
        workflow_id: int,
        execution_id: int,
        filename: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload execution scratch file.

        Returns:
            Storage path
        """
        storage_path = self._get_execution_scratch_path(
            company_id, workflow_id, execution_id, filename
        )

        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)

        success = await self.storage.upload(
            storage_path,
            file_data,
            {"content_type": content_type or "application/octet-stream"},
        )

        if not success:
            raise Exception(f"Failed to upload scratch file {filename}")

        return storage_path

    async def download_file(self, storage_path: str) -> bytes:
        """Download file from storage."""
        content = await self.storage.download(storage_path)
        if not content:
            raise Exception(f"File not found at {storage_path}")
        return content

    async def generate_signed_url(
        self, storage_path: str, expiration_seconds: int = 3600
    ) -> str:
        """
        Generate signed URL for file download.

        Args:
            storage_path: Full storage path
            expiration_seconds: URL expiration time (default 1 hour)

        Returns:
            Signed URL string
        """
        # TODO: Implement signed URL generation in storage provider
        # For now, return a placeholder
        return (
            f"https://storage.example.com/{storage_path}?expires={expiration_seconds}"
        )

    async def delete_file(self, storage_path: str) -> None:
        """Delete file from storage."""
        await self.storage.delete(storage_path)

    async def list_execution_files(
        self, company_id: int, execution_id: int, file_type: str = "outputs"
    ) -> list[str]:
        """
        List all files for an execution.

        Args:
            company_id: Company ID
            execution_id: Execution ID
            file_type: "outputs" or "scratch"

        Returns:
            List of filenames
        """
        prefix = f"companies/{company_id}/executions/{execution_id}/{file_type}/"
        # TODO: Implement list functionality in storage provider
        # For now, return empty list
        return []
