import pytest
from packages.matrices.models.domain.matrix import MatrixCreateModel
from packages.matrices.repositories import MatrixCellRepository
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.matrices.repositories.entity_set_repository import EntitySetRepository
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetCreateModel,
    MatrixEntitySetMemberCreateModel,
)
from unittest.mock import patch

from packages.matrices.services.batch_processing_service import BatchProcessingService
from packages.matrices.models.domain.matrix_enums import MatrixType, EntityType
from packages.qa.models.domain.qa_job import QAJobStatus


@pytest.fixture
def batch_service(test_db, mock_message_queue):
    """Create a BatchProcessingService instance with mocked dependencies."""
    with patch(
        "packages.matrices.services.batch_processing_service.get_message_queue",
        return_value=mock_message_queue,
    ):
        return BatchProcessingService(test_db)


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
@patch("packages.matrices.services.batch_processing_service.get_message_queue")
class TestBatchProcessingService:
    """Unit tests for BatchProcessingService."""

    @pytest.mark.asyncio
    async def test_batch_create_matrix_cells_and_jobs_empty_entity_sets(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        mock_message_queue,
    ):
        """Test batch creation with empty entity set list."""
        mock_get_message_queue.return_value = mock_message_queue
        service = BatchProcessingService(test_db)

        # Test with empty entity sets
        cells, jobs = await service.batch_create_matrix_cells_and_jobs(
            matrix_id=1, entity_set_ids=[], create_qa_jobs=True
        )
        assert cells == []
        assert jobs == []

    @pytest.mark.asyncio
    async def test_process_entity_added_to_set_success(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        sample_subscription,
        mock_message_queue,
    ):
        """Test successful processing of entity added to entity set."""

        mock_get_message_queue.return_value = mock_message_queue
        service = BatchProcessingService(test_db)

        # Create matrix
        matrix_repo = MatrixRepository()
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create entity sets
        entity_set_repo = EntitySetRepository()
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

        # Add initial question member
        member_repo = EntitySetMemberRepository()
        question_member = await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=question_set.id,
                entity_type=EntityType.QUESTION,
                entity_id=1,
                member_order=0,
                company_id=sample_company.id,
            )
        )

        # Add new document member (this is the entity being "added")
        doc_member = await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=doc_set.id,
                entity_type=EntityType.DOCUMENT,
                entity_id=2,
                member_order=0,
                company_id=sample_company.id,
            )
        )

        await test_db.commit()

        # Process new document entity (should create cells but NOT jobs)
        cells, jobs = await service.process_entity_added_to_set(
            matrix_id=matrix.id,
            entity_id=2,
            entity_set_id=doc_set.id,
            create_qa_jobs=False,
        )

        # Should create 1 cell (new doc × 1 existing question)
        assert len(cells) == 1
        assert len(jobs) == 0
        assert cells[0].matrix_id == matrix.id

    @pytest.mark.asyncio
    async def test_process_entity_added_creates_qa_jobs_for_questions(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        sample_subscription,
        mock_message_queue,
    ):
        """Test that adding question creates QA jobs."""

        mock_get_message_queue.return_value = mock_message_queue
        service = BatchProcessingService(test_db)

        # Create matrix
        matrix_repo = MatrixRepository()
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create entity sets
        entity_set_repo = EntitySetRepository()
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

        # Add document and question members
        member_repo = EntitySetMemberRepository()
        await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=doc_set.id,
                entity_type=EntityType.DOCUMENT,
                entity_id=1,
                member_order=0,
                company_id=sample_company.id,
            )
        )
        await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=question_set.id,
                entity_type=EntityType.QUESTION,
                entity_id=1,
                member_order=0,
                company_id=sample_company.id,
            )
        )

        await test_db.commit()

        # Process new question entity (should create cells AND jobs)
        cells, jobs = await service.process_entity_added_to_set(
            matrix_id=matrix.id,
            entity_id=1,
            entity_set_id=question_set.id,
            create_qa_jobs=True,
        )

        # Should create 1 cell and 1 job (1 question × 1 existing doc)
        assert len(cells) == 1
        assert len(jobs) == 1
        assert jobs[0].status == QAJobStatus.QUEUED

    @pytest.mark.asyncio
    async def test_create_jobs_and_queue_for_cells_success(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        mock_message_queue,
        sample_company,
        sample_subscription,
    ):
        """Test successful creation and queueing of jobs for existing cells."""

        mock_get_message_queue.return_value = mock_message_queue
        service = BatchProcessingService(test_db)

        # Create matrix
        matrix_repo = MatrixRepository()
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create entity sets
        entity_set_repo = EntitySetRepository()
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
        member_repo = EntitySetMemberRepository()
        for i in range(3):
            await member_repo.create(
                MatrixEntitySetMemberCreateModel(
                    entity_set_id=doc_set.id,
                    entity_type=EntityType.DOCUMENT,
                    entity_id=i + 1,
                    member_order=i,
                    company_id=sample_company.id,
                )
            )
        await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=question_set.id,
                entity_type=EntityType.QUESTION,
                entity_id=1,
                member_order=0,
                company_id=sample_company.id,
            )
        )

        await test_db.commit()

        # Create cells using the service (which handles entity refs properly)
        cells, _ = await service.process_entity_added_to_set(
            matrix_id=matrix.id,
            entity_id=1,
            entity_set_id=question_set.id,
            create_qa_jobs=False,
        )

        # Should have created 3 cells (3 docs × 1 question)
        assert len(cells) == 3

        # Call the method to create jobs for existing cells
        jobs_created = await service.create_jobs_and_queue_for_cells(cells)

        # Assertions
        assert jobs_created == 3

        # Verify message queue operations occurred
        actual_queue = service.message_queue
        assert actual_queue.declare_queue.called
        # With batch publishing, we call publish_batch once with all messages
        assert actual_queue.publish_batch.call_count == 1

    @pytest.mark.asyncio
    async def test_create_jobs_and_queue_for_cells_empty_list(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        mock_message_queue,
        sample_company,
    ):
        """Test that empty matrix cells list returns 0."""
        mock_get_message_queue.return_value = mock_message_queue
        service = BatchProcessingService(test_db)

        # Call with empty list
        jobs_created = await service.create_jobs_and_queue_for_cells([])

        # Assertions
        assert jobs_created == 0

        # Verify message queue was not used
        actual_queue = service.message_queue
        assert not actual_queue.declare_queue.called
        assert not actual_queue.publish_batch.called

    @pytest.mark.asyncio
    async def test_deduplication_prevents_duplicate_cells(
        self,
        mock_get_message_queue,
        mock_start_span,
        test_db,
        sample_company,
        sample_subscription,
        mock_message_queue,
    ):
        """Test that adding entities incrementally doesn't create duplicate cells."""

        mock_get_message_queue.return_value = mock_message_queue
        service = BatchProcessingService(test_db)

        # Create matrix
        matrix_repo = MatrixRepository()
        matrix = await matrix_repo.create(
            MatrixCreateModel(
                name="Test Matrix",
                workspace_id=1,
                company_id=sample_company.id,
                matrix_type=MatrixType.STANDARD,
            )
        )

        # Create entity sets
        entity_set_repo = EntitySetRepository()
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

        # Add initial members
        member_repo = EntitySetMemberRepository()
        await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=doc_set.id,
                entity_type=EntityType.DOCUMENT,
                entity_id=1,
                member_order=0,
                company_id=sample_company.id,
            )
        )
        await member_repo.create(
            MatrixEntitySetMemberCreateModel(
                entity_set_id=question_set.id,
                entity_type=EntityType.QUESTION,
                entity_id=1,
                member_order=0,
                company_id=sample_company.id,
            )
        )

        await test_db.commit()

        # First: Process doc entity 1 (should create 1 cell)
        cells1, _ = await service.process_entity_added_to_set(
            matrix_id=matrix.id,
            entity_id=1,
            entity_set_id=doc_set.id,
            create_qa_jobs=False,
        )
        assert len(cells1) == 1

        # Second: Try to process same doc entity 1 again (should NOT create duplicate)
        cells2, _ = await service.process_entity_added_to_set(
            matrix_id=matrix.id,
            entity_id=1,
            entity_set_id=doc_set.id,
            create_qa_jobs=False,
        )
        assert len(cells2) == 0  # No new cells created

        # Verify only 1 cell total in database
        cell_repo = MatrixCellRepository()
        all_cells = await cell_repo.get_cells_by_matrix_id(matrix.id)
        assert len(all_cells) == 1
