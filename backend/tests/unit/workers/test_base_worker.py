import pytest
from sqlalchemy.future import select
from unittest.mock import AsyncMock, patch

from common.workers.base_worker import BaseWorker
from packages.qa.models.database.qa_job import QAJobEntity
from packages.qa.models.domain.qa_job import QAJobStatus


class TestableWorker(BaseWorker):
    """Concrete implementation of BaseWorker for testing."""

    def __init__(self, queue_name: str = "test_queue", worker_id: str = None):
        super().__init__(queue_name, worker_id)
        self.processed_messages = []
        self.process_error = None

    async def process_message(self, message):
        """Mock implementation that records processed messages."""
        if self.process_error:
            raise self.process_error
        self.processed_messages.append(message)


class TestBaseWorker:
    """Tests for BaseWorker class with real worker logic."""

    @pytest.fixture
    def test_worker(self, test_db):
        """Create a test worker that actually does database operations."""
        # Store test_db for use in process_message
        db_session = test_db

        class TestWorker(BaseWorker):
            def __init__(self):
                super().__init__("test_queue", "test_worker")
                self.processed_jobs = []

            async def process_message(self, message):
                # Use the test_db from the fixture closure
                # Simulate real worker logic - update a job status
                job_id = message.get("job_id")
                if not job_id:
                    raise ValueError("Missing job_id in message")

                # Find the job in the database using ORM
                result = await db_session.execute(
                    select(QAJobEntity).where(QAJobEntity.id == job_id)
                )
                job = result.scalar_one_or_none()
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                # Update job status to processing
                job.status = QAJobStatus.PROCESSING.value
                await db_session.commit()

                # Simulate some work
                if message.get("should_fail"):
                    job.status = QAJobStatus.FAILED.value
                    await db_session.commit()
                    raise ValueError("Simulated processing error")

                # Mark as completed
                job.status = QAJobStatus.COMPLETED.value
                await db_session.commit()

                self.processed_jobs.append(job_id)

        return TestWorker()

    @pytest.fixture
    async def test_job(
        self,
        test_db,
        sample_company,
        sample_workspace,
        sample_document,
        sample_question,
        sample_matrix,
        sample_matrix_cell,
    ):
        """Create test data in the database."""
        # Create QA job
        job = QAJobEntity(
            matrix_cell_id=sample_matrix_cell.id, status=QAJobStatus.QUEUED.value
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        return {
            "job": job,
            "cell": sample_matrix_cell,
            "document": sample_document,
            "question": sample_question,
            "matrix": sample_matrix,
        }

    @pytest.fixture
    def mock_lock_provider(self):
        """Create a mock lock provider."""
        mock_provider = AsyncMock()
        mock_provider.connect.return_value = None
        mock_provider.disconnect.return_value = None
        return mock_provider

    @pytest.fixture
    def testable_worker(self):
        """Create a testable worker instance."""
        return TestableWorker()

    @pytest.mark.asyncio
    async def test_worker_processes_job_successfully(
        self, test_worker, test_db, test_job
    ):
        """Test that worker successfully processes a job and updates database."""
        message = {"job_id": test_job["job"].id}

        # Process the message
        await test_worker.process_message(message)

        # Verify job was processed
        assert test_job["job"].id in test_worker.processed_jobs

        # Verify database was updated
        await test_db.refresh(test_job["job"])
        assert test_job["job"].status == QAJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_worker_handles_processing_errors(
        self, test_worker, test_db, test_job
    ):
        """Test that worker handles errors and updates job status correctly."""
        message = {"job_id": test_job["job"].id, "should_fail": True}

        # Process should fail
        with pytest.raises(ValueError, match="Simulated processing error"):
            await test_worker.process_message(message)

        # Verify database shows failure
        await test_db.refresh(test_job["job"])
        assert test_job["job"].status == QAJobStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_worker_handles_missing_job_id(self, test_worker, test_db):
        """Test that worker handles missing job_id in message."""
        message = {}  # Missing job_id

        with pytest.raises(ValueError, match="Missing job_id in message"):
            await test_worker.process_message(message)

    @pytest.mark.asyncio
    async def test_worker_handles_nonexistent_job(self, test_worker, test_db):
        """Test that worker handles when job doesn't exist in database."""
        message = {"job_id": 99999}  # Non-existent job

        with pytest.raises(ValueError, match="Job 99999 not found"):
            await test_worker.process_message(message)

    @pytest.mark.asyncio
    async def test_worker_queue_setup_and_cleanup(self, test_worker):
        """Test worker message queue setup and cleanup."""
        mock_queue = AsyncMock()

        with patch(
            "common.workers.base_worker.get_message_queue", return_value=mock_queue
        ):
            # Test setup
            await test_worker.setup()

            mock_queue.connect.assert_called_once()
            mock_queue.declare_queue.assert_called_once_with(
                "test_queue", durable=True, dlq_enabled=True
            )

            # Test cleanup
            await test_worker.cleanup()

            mock_queue.disconnect.assert_called_once()

    def test_worker_initialization(self):
        """Test BaseWorker initialization with different parameters."""
        worker = TestableWorker("my_queue", "my_worker")

        assert worker.queue_name == "my_queue"
        assert worker.worker_id == "my_worker"
        assert worker.message_queue is None
        assert worker.running is False

    def test_worker_initialization_default_worker_id(self):
        """Test BaseWorker initialization with default worker ID."""
        worker = TestableWorker("my_queue")

        assert worker.queue_name == "my_queue"
        assert worker.worker_id.startswith("my_queue_worker_")
        # Check that a UUID was appended
        assert len(worker.worker_id) > len("my_queue_worker_")

    @pytest.mark.asyncio
    async def test_worker_stop_sets_running_false(self, test_worker):
        """Test that stop() sets running to False."""
        test_worker.running = True

        await test_worker.stop()

        assert test_worker.running is False

    @pytest.mark.asyncio
    async def test_worker_setup_with_lock_provider(self, test_worker):
        """Test worker setup when it has a lock provider."""
        mock_queue = AsyncMock()
        mock_lock_provider = AsyncMock()

        test_worker.lock_provider = mock_lock_provider

        with patch(
            "common.workers.base_worker.get_message_queue", return_value=mock_queue
        ):
            await test_worker.setup()

            # Verify both queue and lock provider were connected
            mock_queue.connect.assert_called_once()
            mock_lock_provider.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_cleanup_with_lock_provider(self, test_worker):
        """Test worker cleanup when it has a lock provider."""
        mock_queue = AsyncMock()
        mock_lock_provider = AsyncMock()

        test_worker.message_queue = mock_queue
        test_worker.lock_provider = mock_lock_provider

        await test_worker.cleanup()

        # Verify both queue and lock provider were disconnected
        mock_queue.disconnect.assert_called_once()
        mock_lock_provider.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_setup_handles_lock_provider_errors(self, test_worker):
        """Test that setup handles lock provider connection errors."""
        mock_queue = AsyncMock()
        mock_lock_provider = AsyncMock()
        mock_lock_provider.connect.side_effect = Exception("Lock provider error")

        test_worker.lock_provider = mock_lock_provider

        with patch(
            "common.workers.base_worker.get_message_queue", return_value=mock_queue
        ):
            with pytest.raises(Exception, match="Lock provider error"):
                await test_worker.setup()

    @pytest.mark.asyncio
    async def test_worker_cleanup_handles_errors_gracefully(self, test_worker):
        """Test that cleanup handles errors gracefully and doesn't raise."""
        mock_queue = AsyncMock()
        mock_queue.disconnect.side_effect = Exception("Disconnect error")

        test_worker.message_queue = mock_queue

        # Should not raise an exception
        await test_worker.cleanup()

        mock_queue.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_handler_processes_message(self, testable_worker):
        """Test that _message_handler processes messages correctly."""
        message = {"test_data": "sample message"}

        # This should work and process the message
        await testable_worker._message_handler(message)

        # Verify the message was processed
        assert len(testable_worker.processed_messages) == 1
        assert testable_worker.processed_messages[0] == message

    @pytest.mark.asyncio
    async def test_message_handler_propagates_processing_errors(self, testable_worker):
        """Test that _message_handler propagates errors from process_message."""
        # Set worker to raise an error during processing
        testable_worker.process_error = ValueError("Processing failed")

        message = {"test_data": "sample message"}

        # The error should be propagated up
        with pytest.raises(ValueError, match="Processing failed"):
            await testable_worker._message_handler(message)

    @pytest.mark.asyncio
    async def test_start_worker_already_running_returns_early(self, test_worker):
        """Test that start() returns early if worker is already running."""
        test_worker.running = True

        # This should return immediately without setup
        with patch.object(test_worker, "setup") as mock_setup:
            await test_worker.start()
            mock_setup.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_worker_sets_running_false_on_cleanup(self, test_worker):
        """Test that start() sets running to False during cleanup."""
        mock_queue = AsyncMock()

        # Mock consume to simulate worker processing then stopping
        async def mock_consume(queue_name, handler, auto_ack, prefetch_count=1):
            # Simulate the worker being stopped
            test_worker.running = False

        mock_queue.consume.side_effect = mock_consume

        with patch(
            "common.workers.base_worker.get_message_queue", return_value=mock_queue
        ):
            await test_worker.start()

            # Worker should have running set to False after cleanup
            assert test_worker.running is False

    @pytest.mark.asyncio
    async def test_start_worker_handles_setup_errors(self, test_worker):
        """Test that start() handles setup errors properly."""
        mock_queue = AsyncMock()
        mock_queue.connect.side_effect = Exception("Setup failed")

        with patch(
            "common.workers.base_worker.get_message_queue", return_value=mock_queue
        ):
            with pytest.raises(Exception, match="Setup failed"):
                await test_worker.start()

            # Should have attempted cleanup even after setup failure
            assert test_worker.running is False
