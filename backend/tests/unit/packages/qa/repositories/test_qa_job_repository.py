import pytest

from packages.qa.repositories.qa_job_repository import QAJobRepository
from packages.qa.models.domain.qa_job import (
    QAJobStatus,
    QAJobCreateModel,
    QAJobUpdateWithIdModel,
)


class TestQAJobRepository:
    """Unit tests for QAJobRepository bulk methods."""

    @pytest.fixture
    def qa_job_repo(self, test_db):
        """Create a QAJobRepository instance with real database session."""
        return QAJobRepository()

    @pytest.fixture
    def sample_qa_job_data(self):
        """Sample QA job data for testing."""
        return QAJobCreateModel(
            matrix_cell_id=1,
        )

    @pytest.mark.asyncio
    async def test_bulk_create_from_models(self, qa_job_repo):
        """Test bulk creating QA jobs from domain create models."""
        # Create test models
        create_models = [
            QAJobCreateModel(matrix_cell_id=1, status=QAJobStatus.QUEUED),
            QAJobCreateModel(matrix_cell_id=2, status=QAJobStatus.QUEUED),
            QAJobCreateModel(
                matrix_cell_id=3,
                status=QAJobStatus.PROCESSING,
                worker_message_id="worker-123",
            ),
        ]

        # Call bulk create
        result = await qa_job_repo.bulk_create_from_models(create_models)

        # Assertions
        assert len(result) == 3
        for i, job in enumerate(result):
            assert job.id is not None  # Should have auto-generated ID
            assert job.matrix_cell_id == create_models[i].matrix_cell_id
            # Both should be enum objects after processing
            expected_status = (
                create_models[i].status
                if isinstance(create_models[i].status, QAJobStatus)
                else QAJobStatus(create_models[i].status)
            )
            assert job.status == expected_status
            assert job.worker_message_id == create_models[i].worker_message_id
            assert job.created_at is not None
            assert job.updated_at is not None

    @pytest.mark.asyncio
    async def test_bulk_create_from_models_empty_list(self, qa_job_repo):
        """Test bulk creating with empty list returns empty list."""
        result = await qa_job_repo.bulk_create_from_models([])
        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_update_by_id(self, qa_job_repo, sample_qa_job_data):
        """Test bulk updating QA jobs by ID."""
        # Create test jobs first
        job1 = await qa_job_repo.create(
            QAJobCreateModel(
                matrix_cell_id=1,
            )
        )
        job2 = await qa_job_repo.create(
            QAJobCreateModel(
                matrix_cell_id=2,
            )
        )
        job3 = await qa_job_repo.create(
            QAJobCreateModel(
                matrix_cell_id=3,
            )
        )

        # Update data - jobs 1 and 2 to PROCESSING with worker_message_id, job 3 to COMPLETED
        updates = [
            QAJobUpdateWithIdModel(
                id=job1.id,
                status=QAJobStatus.PROCESSING.value,
                worker_message_id="worker-1",
            ),
            QAJobUpdateWithIdModel(
                id=job2.id,
                status=QAJobStatus.PROCESSING.value,
                worker_message_id="worker-2",
            ),
            QAJobUpdateWithIdModel(
                id=job3.id,
                status=QAJobStatus.COMPLETED.value,
                error_message=None,
            ),
        ]

        # Call bulk update
        updated_count = await qa_job_repo.bulk_update_by_id(updates)

        # Assertions
        assert updated_count == 3

        # Verify updates were applied
        updated_job1 = await qa_job_repo.get(job1.id)
        updated_job2 = await qa_job_repo.get(job2.id)
        updated_job3 = await qa_job_repo.get(job3.id)

        assert updated_job1.status == QAJobStatus.PROCESSING
        assert updated_job1.worker_message_id == "worker-1"
        assert updated_job2.status == QAJobStatus.PROCESSING
        assert updated_job2.worker_message_id == "worker-2"
        assert updated_job3.status == QAJobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_bulk_update_by_id_empty_list(self, qa_job_repo):
        """Test bulk updating with empty list returns 0."""
        result = await qa_job_repo.bulk_update_by_id([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_update_by_id_worker_message_ids(
        self, qa_job_repo, sample_qa_job_data
    ):
        """Test bulk updating only worker_message_id fields (common use case)."""
        # Create test jobs
        jobs = []
        for i in range(3):
            job = await qa_job_repo.create(
                QAJobCreateModel(
                    matrix_cell_id=i + 1,
                )
            )
            jobs.append(job)

        # Update worker_message_ids for all jobs
        updates = [
            QAJobUpdateWithIdModel(id=jobs[0].id, worker_message_id="msg-001"),
            QAJobUpdateWithIdModel(id=jobs[1].id, worker_message_id="msg-002"),
            QAJobUpdateWithIdModel(id=jobs[2].id, worker_message_id="msg-003"),
        ]

        # Call bulk update
        updated_count = await qa_job_repo.bulk_update_by_id(updates)
        assert updated_count == 3

        # Verify updates were applied efficiently (all should have same update pattern)
        for i, job in enumerate(jobs):
            updated_job = await qa_job_repo.get(job.id)
            assert updated_job.worker_message_id == f"msg-{i+1:03d}"
            # Status should remain unchanged
            assert updated_job.status == QAJobStatus.QUEUED

    @pytest.mark.asyncio
    async def test_bulk_update_by_id_mixed_updates(
        self, qa_job_repo, sample_qa_job_data
    ):
        """Test bulk updating with mixed update patterns."""
        # Create test jobs
        jobs = []
        for i in range(4):
            job = await qa_job_repo.create(
                QAJobCreateModel(
                    matrix_cell_id=i + 1,
                )
            )
            jobs.append(job)

        # Mixed updates - some jobs get worker_message_id, others get status change
        updates = [
            QAJobUpdateWithIdModel(id=jobs[0].id, worker_message_id="worker-123"),
            QAJobUpdateWithIdModel(id=jobs[1].id, worker_message_id="worker-456"),
            QAJobUpdateWithIdModel(
                id=jobs[2].id,
                status=QAJobStatus.FAILED.value,
                error_message="Processing failed",
            ),
            QAJobUpdateWithIdModel(id=jobs[3].id, status=QAJobStatus.COMPLETED.value),
        ]

        # Call bulk update
        updated_count = await qa_job_repo.bulk_update_by_id(updates)
        assert updated_count == 4

        # Verify mixed updates were applied correctly
        updated_job1 = await qa_job_repo.get(jobs[0].id)
        updated_job2 = await qa_job_repo.get(jobs[1].id)
        updated_job3 = await qa_job_repo.get(jobs[2].id)
        updated_job4 = await qa_job_repo.get(jobs[3].id)

        assert updated_job1.worker_message_id == "worker-123"
        assert updated_job1.status == QAJobStatus.QUEUED  # Unchanged

        assert updated_job2.worker_message_id == "worker-456"
        assert updated_job2.status == QAJobStatus.QUEUED  # Unchanged

        assert updated_job3.status == QAJobStatus.FAILED
        assert updated_job3.error_message == "Processing failed"

        assert updated_job4.status == QAJobStatus.COMPLETED
