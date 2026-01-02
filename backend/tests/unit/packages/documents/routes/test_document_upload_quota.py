"""
Unit tests for document upload quota enforcement.

Tests that quota checks are properly enforced on all document upload endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from io import BytesIO

from datetime import datetime, timezone

from fastapi import HTTPException

from tests.fixtures import SAMPLE_WORKSPACE_DATA, SAMPLE_MATRIX_DATA, SAMPLE_PDF_CONTENT
from packages.billing.models.domain.usage import QuotaCheck


@pytest.mark.asyncio
class TestDocumentUploadQuota:
    """Tests for quota enforcement on document upload endpoints."""

    async def _create_matrix_with_entity_set(
        self, client: AsyncClient, sample_company
    ) -> tuple[dict, int]:
        """Helper to create a matrix and return matrix data + document entity set ID."""
        company = sample_company.__dict__

        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json={**SAMPLE_WORKSPACE_DATA}
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {
            **SAMPLE_MATRIX_DATA,
            "workspaceId": workspace["id"],
            "companyId": company["id"],
        }
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get document entity set ID
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix['id']}/entity-sets"
        )
        entity_sets = entity_sets_response.json()["entitySets"]
        document_entity_set = next(
            es for es in entity_sets if es["entityType"] == "document"
        )

        return matrix, document_entity_set["id"]

    # =========================================================================
    # Tests for upload_document (POST /matrices/{id}/documents/)
    # =========================================================================

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_document_quota_allowed(
        self,
        mock_quota_service_class,
        mock_get_message_queue,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
        sample_company,
        sample_subscription,
    ):
        """Test upload_document succeeds when storage quota is available."""
        # Setup mocks
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_message_queue.return_value = mock_message_queue

        # Mock quota service to allow upload (both document and storage quotas)
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=5,
                limit=50,
                remaining=45,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="storage_bytes",
                current_usage=50_000_000,
                limit=1_000_000_000,
                remaining=950_000_000,
                percentage_used=5.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Create matrix and get entity set
        matrix, entity_set_id = await self._create_matrix_with_entity_set(
            client, sample_company
        )

        # Upload document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
            files=files,
        )

        # Assert upload succeeded
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["contentType"] == "application/pdf"

        # Verify storage quota was checked
        mock_quota_service.check_storage_quota.assert_called_once()
        call_kwargs = mock_quota_service.check_storage_quota.call_args.kwargs
        assert call_kwargs["company_id"] == sample_company.id
        assert "file_size_bytes" in call_kwargs

    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_document_storage_quota_exceeded(
        self,
        mock_quota_service_class,
        client: AsyncClient,
        sample_company,
        sample_subscription,
    ):
        """Test upload_document fails with 402 when storage quota exceeded."""
        # Mock quota service - document quota OK, storage quota exceeded
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=5,
                limit=50,
                remaining=45,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=False,
                metric_name="storage_bytes",
                current_usage=990_000_000,
                limit=1_000_000_000,
                remaining=10_000_000,
                percentage_used=99.0,
                warning_threshold_reached=True,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Create matrix and get entity set
        matrix, entity_set_id = await self._create_matrix_with_entity_set(
            client, sample_company
        )

        # Attempt to upload document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
            files=files,
        )

        # Assert upload was denied
        assert response.status_code == 402
        data = response.json()
        assert "detail" in data
        # Error message should mention quota/limit/storage
        assert any(
            word in data["detail"].lower() for word in ["quota", "limit", "storage"]
        )

    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_document_document_quota_exceeded(
        self,
        mock_quota_service_class,
        client: AsyncClient,
        sample_company,
        sample_subscription,
    ):
        """Test upload_document fails with 429 when document quota exceeded."""
        # Mock quota service - document quota exceeded (raises 429)
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            side_effect=HTTPException(
                status_code=429,
                detail="Monthly document upload limit reached (10). Upgrade your plan for more.",
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Create matrix and get entity set
        matrix, entity_set_id = await self._create_matrix_with_entity_set(
            client, sample_company
        )

        # Attempt to upload document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
            files=files,
        )

        # Assert upload was denied with 429
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "document" in data["detail"].lower()

        # Storage quota should NOT have been checked (document check happens first)
        mock_quota_service.check_storage_quota.assert_not_called()

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_document_quota_at_limit_succeeds(
        self,
        mock_quota_service_class,
        mock_get_message_queue,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
        sample_company,
        sample_subscription,
    ):
        """Test upload_document succeeds when exactly at quota limit."""
        # Setup mocks
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_message_queue.return_value = mock_message_queue

        # Mock quota service - exactly at limit but still allowed
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=49,
                limit=50,
                remaining=1,
                percentage_used=98.0,
                warning_threshold_reached=True,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="storage_bytes",
                current_usage=990_000_000,
                limit=1_000_000_000,
                remaining=10_000_000,
                percentage_used=99.0,
                warning_threshold_reached=True,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Create matrix and get entity set
        matrix, entity_set_id = await self._create_matrix_with_entity_set(
            client, sample_company
        )

        # Upload document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
            files=files,
        )

        # Assert upload succeeded
        assert response.status_code == 200

    # =========================================================================
    # Tests for upload_standalone_document (POST /documents/)
    # =========================================================================

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_standalone_document_quota_allowed(
        self,
        mock_quota_service_class,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        sample_company,
        sample_subscription,
    ):
        """Test upload_standalone_document succeeds when quota is available."""
        # Setup mocks
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        # Mock quota service to allow upload (both quotas)
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=5,
                limit=50,
                remaining=45,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="storage_bytes",
                current_usage=50_000_000,
                limit=1_000_000_000,
                remaining=950_000_000,
                percentage_used=5.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Upload standalone document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post("/api/v1/documents/", files=files)

        # Assert upload succeeded
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"

        # Verify quota was checked
        mock_quota_service.check_storage_quota.assert_called_once()

    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_standalone_document_quota_exceeded(
        self,
        mock_quota_service_class,
        client: AsyncClient,
        sample_company,
        sample_subscription,
    ):
        """Test upload_standalone_document fails with 402 when storage quota exceeded."""
        # Mock quota service - document OK, storage exceeded
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=5,
                limit=50,
                remaining=45,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=False,
                metric_name="storage_bytes",
                current_usage=995_000_000,
                limit=1_000_000_000,
                remaining=5_000_000,
                percentage_used=99.5,
                warning_threshold_reached=True,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Attempt to upload standalone document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post("/api/v1/documents/", files=files)

        # Assert upload was denied
        assert response.status_code == 402
        data = response.json()
        assert "detail" in data

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_standalone_document_over_limit_fails(
        self,
        mock_quota_service_class,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        sample_company,
        sample_subscription,
    ):
        """Test upload_standalone_document fails when over storage limit."""
        # Setup storage mocks
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        # Mock quota service - document OK, storage over limit
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=5,
                limit=50,
                remaining=45,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=False,
                metric_name="storage_bytes",
                current_usage=1_001_000_000,
                limit=1_000_000_000,
                remaining=-1_000_000,
                percentage_used=100.1,
                warning_threshold_reached=True,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Attempt to upload standalone document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post("/api/v1/documents/", files=files)

        # Assert upload was denied
        assert response.status_code == 402

    # =========================================================================
    # Tests for upload_documents_from_urls (POST /matrices/{id}/documents/from-urls/)
    # =========================================================================

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_documents_from_urls_quota_allowed(
        self,
        mock_quota_service_class,
        mock_get_message_queue,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
        sample_company,
        sample_subscription,
    ):
        """Test upload_documents_from_urls succeeds when quota is available."""
        # Setup mocks
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_message_queue.return_value = mock_message_queue

        # Mock quota service to allow upload (both quotas)
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=5,
                limit=50,
                remaining=45,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="storage_bytes",
                current_usage=50_000_000,
                limit=1_000_000_000,
                remaining=950_000_000,
                percentage_used=5.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Create matrix and get entity set
        matrix, entity_set_id = await self._create_matrix_with_entity_set(
            client, sample_company
        )

        # Upload documents from URLs
        request_data = {
            "urls": [
                "https://example.com/doc1.pdf",
                "https://example.com/doc2.pdf",
            ],
        }
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/from-urls/?entitySetId={entity_set_id}",
            json=request_data,
        )

        # Assert upload succeeded
        assert response.status_code == 200

        # Verify both quotas were checked
        mock_quota_service.check_document_quota.assert_called_once()
        mock_quota_service.check_storage_quota.assert_called_once()
        call_kwargs = mock_quota_service.check_storage_quota.call_args.kwargs
        assert call_kwargs["company_id"] == sample_company.id
        assert call_kwargs["file_size_bytes"] == 0

    @patch("packages.documents.routes.documents.QuotaService")
    async def test_upload_documents_from_urls_quota_exceeded(
        self,
        mock_quota_service_class,
        client: AsyncClient,
        sample_company,
        sample_subscription,
    ):
        """Test upload_documents_from_urls fails when already over storage quota."""
        # Mock quota service - document OK, storage exceeded
        mock_quota_service = AsyncMock()
        mock_quota_service.check_document_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=True,
                metric_name="documents",
                current_usage=5,
                limit=50,
                remaining=45,
                percentage_used=10.0,
                warning_threshold_reached=False,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service.check_storage_quota = AsyncMock(
            return_value=QuotaCheck(
                allowed=False,
                metric_name="storage_bytes",
                current_usage=1_000_000_000,
                limit=1_000_000_000,
                remaining=0,
                percentage_used=100.0,
                warning_threshold_reached=True,
                period_type="monthly",
                period_end=datetime.now(timezone.utc),
            )
        )
        mock_quota_service_class.return_value = mock_quota_service

        # Create matrix and get entity set
        matrix, entity_set_id = await self._create_matrix_with_entity_set(
            client, sample_company
        )

        # Attempt to upload documents from URLs
        request_data = {
            "urls": [f"https://example.com/doc{i}.pdf" for i in range(5)],
        }
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/from-urls/?entitySetId={entity_set_id}",
            json=request_data,
        )

        # Assert upload was denied
        assert response.status_code == 402
        data = response.json()
        assert "detail" in data
