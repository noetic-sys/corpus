import pytest
from unittest.mock import patch

from packages.matrices.models.domain.matrix_enums import (
    MatrixType,
    EntityType,
    EntityRole,
)
from packages.matrices.services.reprocessing_service import ReprocessingService
from packages.matrices.models.schemas.matrix import (
    MatrixReprocessRequest,
    EntitySetFilter,
)
from packages.matrices.models.domain.matrix import MatrixCreateModel
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.matrices.repositories.entity_set_repository import EntitySetRepository
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetCreateModel,
    MatrixEntitySetMemberCreateModel,
)


@pytest.fixture
def reprocessing_service(test_db, mock_message_queue):
    """Create a ReprocessingService instance with mocked dependencies."""
    with patch(
        "packages.matrices.services.batch_processing_service.get_message_queue",
        return_value=mock_message_queue,
    ):
        return ReprocessingService(test_db)


# Mock both tracing and the message queue BEFORE importing anything
@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
@patch("packages.matrices.services.batch_processing_service.get_message_queue")
class TestReprocessingService:
    """Unit tests for ReprocessingService."""

    @pytest.mark.asyncio
    async def test_reprocess_matrix_cells_whole_matrix(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        sample_subscription,
        mock_message_queue,
        reprocessing_service,
    ):
        """Test reprocessing entire matrix."""
        mock_get_message_queue.return_value = mock_message_queue

        # Create matrix
        matrix_repo = MatrixRepository(test_db)
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create entity sets
        entity_set_repo = EntitySetRepository(test_db)
        doc_set = await entity_set_repo.create(
            MatrixEntitySetCreateModel(
                matrix_id=matrix.id,
                company_id=sample_company.id,
                name="Documents",
                entity_type=EntityType.DOCUMENT,
            )
        )
        question_set = await entity_set_repo.create(
            MatrixEntitySetCreateModel(
                matrix_id=matrix.id,
                company_id=sample_company.id,
                name="Questions",
                entity_type=EntityType.QUESTION,
            )
        )

        # Add members
        member_repo = EntitySetMemberRepository(test_db)
        for i in range(2):
            await member_repo.create(
                MatrixEntitySetMemberCreateModel(
                    entity_set_id=doc_set.id,
                    entity_type=EntityType.DOCUMENT,
                    entity_id=i + 1,
                    member_order=i,
                    company_id=sample_company.id,
                )
            )
        for i in range(2):
            await member_repo.create(
                MatrixEntitySetMemberCreateModel(
                    entity_set_id=question_set.id,
                    entity_type=EntityType.QUESTION,
                    entity_id=i + 1,
                    member_order=i,
                    company_id=sample_company.id,
                )
            )

        await test_db.commit()

        # Create cells using batch service
        cells, jobs = (
            await reprocessing_service.batch_processing_service.batch_create_matrix_cells_and_jobs(
                matrix_id=matrix.id,
                entity_set_ids=[doc_set.id, question_set.id],
                create_qa_jobs=False,
            )
        )

        # Should have 4 cells (2 docs × 2 questions)
        assert len(cells) == 4

        # Create request for whole matrix
        request = MatrixReprocessRequest(whole_matrix=True)

        # Call the service
        result = await reprocessing_service.reprocess_matrix_cells(matrix.id, request)

        # Assertions
        assert result == 4  # All 4 cells should be reprocessed

        # Verify message queue operations occurred
        assert mock_message_queue.declare_queue.called
        assert mock_message_queue.publish_batch.called

    @pytest.mark.asyncio
    async def test_reprocess_matrix_cells_by_entity_set_filter(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        sample_subscription,
        mock_message_queue,
        reprocessing_service,
    ):
        """Test reprocessing cells by entity set filter."""
        mock_get_message_queue.return_value = mock_message_queue

        # Create matrix
        matrix_repo = MatrixRepository(test_db)
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create entity sets
        entity_set_repo = EntitySetRepository(test_db)
        doc_set = await entity_set_repo.create(
            MatrixEntitySetCreateModel(
                matrix_id=matrix.id,
                company_id=sample_company.id,
                name="Documents",
                entity_type=EntityType.DOCUMENT,
            )
        )
        question_set = await entity_set_repo.create(
            MatrixEntitySetCreateModel(
                matrix_id=matrix.id,
                company_id=sample_company.id,
                name="Questions",
                entity_type=EntityType.QUESTION,
            )
        )

        # Add members
        member_repo = EntitySetMemberRepository(test_db)
        for i in range(2):
            await member_repo.create(
                MatrixEntitySetMemberCreateModel(
                    entity_set_id=doc_set.id,
                    entity_type=EntityType.DOCUMENT,
                    entity_id=i + 1,
                    member_order=i,
                    company_id=sample_company.id,
                )
            )
        for i in range(2):
            await member_repo.create(
                MatrixEntitySetMemberCreateModel(
                    entity_set_id=question_set.id,
                    entity_type=EntityType.QUESTION,
                    entity_id=i + 1,
                    member_order=i,
                    company_id=sample_company.id,
                )
            )

        await test_db.commit()

        # Create cells
        cells, _ = (
            await reprocessing_service.batch_processing_service.batch_create_matrix_cells_and_jobs(
                matrix_id=matrix.id,
                entity_set_ids=[doc_set.id, question_set.id],
                create_qa_jobs=False,
            )
        )

        assert len(cells) == 4  # 2 docs × 2 questions

        # Create request for specific document (entity_id=1 in doc_set)
        request = MatrixReprocessRequest(
            entity_set_filters=[
                EntitySetFilter(
                    entity_set_id=doc_set.id,
                    entity_ids=[1],
                    role=EntityRole.DOCUMENT,
                )
            ]
        )

        # Call the service
        result = await reprocessing_service.reprocess_matrix_cells(matrix.id, request)

        # Should reprocess 2 cells (1 doc × 2 questions)
        assert result == 2

    @pytest.mark.asyncio
    async def test_reprocess_matrix_cells_by_cell_ids(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        sample_subscription,
        mock_message_queue,
        reprocessing_service,
    ):
        """Test reprocessing cells by specific cell IDs."""
        mock_get_message_queue.return_value = mock_message_queue

        # Create matrix
        matrix_repo = MatrixRepository(test_db)
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create entity sets
        entity_set_repo = EntitySetRepository(test_db)
        doc_set = await entity_set_repo.create(
            MatrixEntitySetCreateModel(
                matrix_id=matrix.id,
                company_id=sample_company.id,
                name="Documents",
                entity_type=EntityType.DOCUMENT,
            )
        )
        question_set = await entity_set_repo.create(
            MatrixEntitySetCreateModel(
                matrix_id=matrix.id,
                company_id=sample_company.id,
                name="Questions",
                entity_type=EntityType.QUESTION,
            )
        )

        # Add members
        member_repo = EntitySetMemberRepository(test_db)
        await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=doc_set.id,
                entity_type=EntityType.DOCUMENT,
                entity_id=1,
                member_order=0,
                company_id=sample_company.id,
            )
        )
        for i in range(2):
            await member_repo.create(
                MatrixEntitySetMemberCreateModel(
                    entity_set_id=question_set.id,
                    entity_type=EntityType.QUESTION,
                    entity_id=i + 1,
                    member_order=i,
                    company_id=sample_company.id,
                )
            )

        await test_db.commit()

        # Create cells
        cells, _ = (
            await reprocessing_service.batch_processing_service.batch_create_matrix_cells_and_jobs(
                matrix_id=matrix.id,
                entity_set_ids=[doc_set.id, question_set.id],
                create_qa_jobs=False,
            )
        )

        assert len(cells) == 2  # 1 doc × 2 questions

        # Create request for specific cell
        request = MatrixReprocessRequest(cell_ids=[cells[0].id])

        # Call the service
        result = await reprocessing_service.reprocess_matrix_cells(matrix.id, request)

        # Assertions
        assert result == 1  # Only 1 specific cell should be reprocessed

    @pytest.mark.asyncio
    async def test_reprocess_matrix_cells_no_matching_cells(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        sample_subscription,
        mock_message_queue,
        reprocessing_service,
    ):
        """Test reprocessing when no cells match the criteria."""
        mock_get_message_queue.return_value = mock_message_queue

        # Create matrix
        matrix_repo = MatrixRepository(test_db)
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create request for non-existent entity
        request = MatrixReprocessRequest(
            entity_set_filters=[
                EntitySetFilter(
                    entity_set_id=999,
                    entity_ids=[999],
                    role=EntityRole.DOCUMENT,
                )
            ]
        )

        # Call the service
        result = await reprocessing_service.reprocess_matrix_cells(matrix.id, request)

        # Assertions
        assert result == 0  # No cells should be reprocessed

        # Verify message queue was not used since no cells to process
        assert not mock_message_queue.publish_batch.called
