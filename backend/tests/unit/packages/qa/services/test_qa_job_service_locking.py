import pytest
import hashlib

from packages.documents.models.domain.document import ExtractionStatus
from packages.qa.services.qa_job_service import QAJobService
from packages.qa.models.domain.qa_job import (
    QAJobStatus,
    QAJobCreateModel,
    QueuePendingCellsResult,
)
from packages.matrices.models.domain.matrix import MatrixCellStatus, MatrixCellModel
from packages.matrices.models.database.matrix import MatrixCellEntity
from common.providers.messaging.constants import QueueName


class TestQAJobServiceWithLocking:
    """Test QA Job Service with real database and repositories."""

    @pytest.fixture
    def db_session(self, test_db):
        """Get a test database session using conftest fixture."""
        return test_db

    @pytest.fixture
    def qa_job_service(self, db_session, mock_message_queue):
        """Create QAJobService instance with real repositories."""
        service = QAJobService(db_session)
        service.message_queue = mock_message_queue
        return service

    @pytest.fixture
    async def test_data(
        self,
        db_session,
        sample_workspace,
        sample_matrix,
        sample_document,
        sample_matrix_cell,
        sample_question,
    ):
        """Create test data in the real database."""
        session = db_session
        sample_document.extraction_status = ExtractionStatus.COMPLETED
        sample_document.extracted_content_path = "extracted/test_doc.md"
        session.add(sample_document)
        await session.commit()
        await session.refresh(sample_document)

        return {
            "matrix": sample_matrix,
            "document": sample_document,
            "question": sample_question,
            "cell": sample_matrix_cell,
        }

    @pytest.fixture
    def sample_matrix_cell_model(self, sample_matrix_cell):
        """Convert test data to domain model."""
        cell = sample_matrix_cell
        return MatrixCellModel(
            id=cell.id,
            company_id=cell.company_id,
            matrix_id=cell.matrix_id,
            cell_type=cell.cell_type,
            status=cell.status,
            created_at=cell.created_at,
            updated_at=cell.updated_at,
            cell_signature=cell.cell_signature,
        )

    @pytest.mark.asyncio
    async def test_create_and_queue_job_always_creates_new_job(
        self,
        qa_job_service,
        sample_matrix_cell_model,
        mock_message_queue,
        db_session,
    ):
        """Test that create_and_queue_job always creates a new job (no blocking)."""
        # Setup message queue mocks
        mock_message_queue.declare_queue.return_value = True
        mock_message_queue.publish.return_value = True

        # Call the method
        result = await qa_job_service.create_and_queue_job(sample_matrix_cell_model)

        # Verify new job was created in the database
        assert result is not None
        assert result.matrix_cell_id == sample_matrix_cell_model.id
        assert result.status == QAJobStatus.QUEUED

        # Verify job was queued
        mock_message_queue.publish.assert_called_once()

        # Verify job exists in database
        jobs = await qa_job_service.qa_job_repo.get_by_matrix_cell_id(
            sample_matrix_cell_model.id
        )
        assert len(jobs) == 1
        assert jobs[0].id == result.id

    @pytest.mark.asyncio
    async def test_create_and_queue_job_multiple_jobs_allowed(
        self,
        qa_job_service,
        sample_matrix_cell_model,
        mock_message_queue,
        db_session,
    ):
        """Test that multiple jobs can be created for the same cell."""
        # Setup message queue mocks
        mock_message_queue.declare_queue.return_value = True
        mock_message_queue.publish.return_value = True

        # Create first job
        result1 = await qa_job_service.create_and_queue_job(sample_matrix_cell_model)

        # Create second job for same cell (should succeed)
        result2 = await qa_job_service.create_and_queue_job(sample_matrix_cell_model)

        # Both jobs should be created
        assert result1 is not None
        assert result2 is not None
        assert result1.id != result2.id
        assert mock_message_queue.publish.call_count == 2

        # Verify both jobs exist in database
        jobs = await qa_job_service.qa_job_repo.get_by_matrix_cell_id(
            sample_matrix_cell_model.id
        )
        assert len(jobs) == 2
        job_ids = {job.id for job in jobs}
        assert result1.id in job_ids
        assert result2.id in job_ids

    @pytest.mark.asyncio
    async def test_create_and_queue_job_handles_publish_failure(
        self,
        qa_job_service,
        sample_matrix_cell_model,
        mock_message_queue,
        db_session,
    ):
        """Test handling when message publishing fails."""
        # Setup mocks - job creation succeeds, publishing fails
        mock_message_queue.declare_queue.return_value = True
        mock_message_queue.publish.return_value = False

        # Call the method
        result = await qa_job_service.create_and_queue_job(sample_matrix_cell_model)

        # Verify job was created but marked as failed due to publish failure
        mock_message_queue.publish.assert_called_once()

        # Should return None when publishing fails
        assert result is None

        # Verify job exists in database but is marked as failed
        jobs = await qa_job_service.qa_job_repo.get_by_matrix_cell_id(
            sample_matrix_cell_model.id
        )
        assert len(jobs) == 1
        assert jobs[0].status == QAJobStatus.FAILED

    @pytest.mark.asyncio
    async def test_publish_job_message_creates_correct_message(
        self,
        qa_job_service,
        sample_matrix_cell_model,
        mock_message_queue,
        db_session,
    ):
        """Test that publish_job_message creates the correct message format."""
        # Create a real job in the database first
        job_data = QAJobCreateModel(
            matrix_cell_id=sample_matrix_cell_model.id,
        )
        job = await qa_job_service.qa_job_repo.create(job_data)

        mock_message_queue.declare_queue.return_value = True
        mock_message_queue.publish.return_value = True

        result = await qa_job_service.publish_job_message(job, sample_matrix_cell_model)

        # Verify correct message was published
        mock_message_queue.publish.assert_called_once_with(
            QueueName.QA_WORKER,
            {
                "job_id": job.id,
                "matrix_cell_id": sample_matrix_cell_model.id,
            },
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_queue_pending_cells_processes_all_cells(
        self, qa_job_service, mock_message_queue, db_session, test_data, sample_company
    ):
        """Test that queue_pending_cells processes all pending cells."""
        data = test_data

        # Create additional pending cells
        for i in range(2):
            cell = MatrixCellEntity(
                matrix_id=data["matrix"].id,
                company_id=sample_company.id,
                cell_type="standard",
                status=MatrixCellStatus.PENDING.value,
                cell_signature=hashlib.md5(f"test_qa_{i}".encode()).hexdigest(),
            )
            db_session.add(cell)
        await db_session.commit()

        # Setup message queue mocks
        mock_message_queue.declare_queue.return_value = True
        mock_message_queue.publish.return_value = True

        result = await qa_job_service.queue_pending_cells()

        # Verify all cells were processed (original + 2 new = 3 total)
        assert isinstance(result, QueuePendingCellsResult)
        assert result.total_pending_cells == 3
        assert result.queued == 3
        assert result.failed == 0

        # Verify jobs were created in database
        all_jobs = await qa_job_service.qa_job_repo.get_by_status(QAJobStatus.QUEUED)
        assert len(all_jobs) == 3

    @pytest.mark.asyncio
    async def test_create_qa_job_sets_correct_fields(
        self,
        qa_job_service,
        sample_matrix_cell_model,
        db_session,
    ):
        """Test that create_qa_job sets all required fields correctly."""
        job = await qa_job_service.create_qa_job(sample_matrix_cell_model.id)

        assert job.matrix_cell_id == sample_matrix_cell_model.id
        assert job.status == QAJobStatus.QUEUED
        assert job.worker_message_id is None
        assert job.error_message is None
        assert job.created_at is not None
        assert job.updated_at is not None
        assert job.completed_at is None

        # Verify job exists in database
        db_job = await qa_job_service.qa_job_repo.get(job.id)
        assert db_job is not None
        assert db_job.matrix_cell_id == sample_matrix_cell_model.id

    @pytest.mark.asyncio
    async def test_multiple_jobs_can_be_queued_for_same_cell(
        self,
        qa_job_service,
        sample_matrix_cell_model,
        mock_message_queue,
        db_session,
    ):
        """Test that multiple QA jobs can be queued for the same matrix cell."""
        # Setup message queue mocks
        mock_message_queue.declare_queue.return_value = True
        mock_message_queue.publish.return_value = True

        # Create first job
        job1 = await qa_job_service.create_and_queue_job(sample_matrix_cell_model)

        # Create second job for the same cell (should succeed)
        job2 = await qa_job_service.create_and_queue_job(sample_matrix_cell_model)

        # Create third job for the same cell (should succeed)
        job3 = await qa_job_service.create_and_queue_job(sample_matrix_cell_model)

        # All jobs should be created successfully
        assert job1 is not None
        assert job2 is not None
        assert job3 is not None

        # All jobs should have different IDs
        assert job1.id != job2.id
        assert job1.id != job3.id
        assert job2.id != job3.id

        # All jobs should be for the same cell
        assert job1.matrix_cell_id == sample_matrix_cell_model.id
        assert job2.matrix_cell_id == sample_matrix_cell_model.id
        assert job3.matrix_cell_id == sample_matrix_cell_model.id

        # All jobs should be queued status initially
        assert job1.status == QAJobStatus.QUEUED
        assert job2.status == QAJobStatus.QUEUED
        assert job3.status == QAJobStatus.QUEUED

        # Verify 3 messages were published to the queue
        assert mock_message_queue.publish.call_count == 3

        # Verify all jobs exist in database
        jobs = await qa_job_service.qa_job_repo.get_by_matrix_cell_id(
            sample_matrix_cell_model.id
        )
        assert len(jobs) == 3

        job_ids = {job.id for job in jobs}
        assert job1.id in job_ids
        assert job2.id in job_ids
        assert job3.id in job_ids
