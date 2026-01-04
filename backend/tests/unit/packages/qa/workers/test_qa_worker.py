import pytest
from pydantic import ValidationError
from packages.documents.models.database.document import ExtractionStatus
from unittest.mock import AsyncMock, patch

from packages.qa.workers.qa_worker import QAWorker
from packages.qa.models.database.qa_job import QAJobEntity
from packages.qa.models.domain.qa_job import QAJobStatus
from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.qa.models.domain.answer_data import TextAnswerData, AIAnswerSet
from common.providers.locking.interface import DistributedLockInterface
from packages.matrices.services.matrix_service import MatrixService
from common.providers.messaging.messages import QAJobMessage
from common.providers.messaging.constants import QueueName


class TestQAWorker:
    """Tests for QAWorker class with real database."""

    @pytest.fixture
    def mock_lock_provider(self):
        """Create mock lock provider."""
        mock_provider = AsyncMock(spec=DistributedLockInterface)
        return mock_provider

    @pytest.fixture
    def qa_worker(self, mock_lock_provider):
        """Create QAWorker instance with mocked services."""
        worker = QAWorker()
        worker.lock_provider = mock_lock_provider  # Override the lock provider
        return worker

    @pytest.fixture
    async def test_data(
        self,
        test_db,
        sample_workspace,
        sample_document,
        sample_matrix,
        sample_question,
        sample_matrix_cell,
    ):
        """Create test data in the database."""
        # Update sample_document to have COMPLETED extraction status
        sample_document.extraction_status = ExtractionStatus.COMPLETED
        sample_document.extracted_content_path = "extracted/test_doc.md"
        test_db.add(sample_document)
        await test_db.commit()
        await test_db.refresh(sample_document)

        # Create QA job
        job = QAJobEntity(
            matrix_cell_id=sample_matrix_cell.id, status=QAJobStatus.QUEUED.value
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        return {
            "matrix": sample_matrix,
            "document": sample_document,
            "question": sample_question,
            "cell": sample_matrix_cell,
            "job": job,
        }

    @pytest.fixture
    def sample_message(self, test_data):
        """Sample message based on real test data."""
        return QAJobMessage(
            job_id=test_data["job"].id,
            matrix_cell_id=test_data["cell"].id,
        )

    @pytest.mark.asyncio
    @patch("packages.matrices.strategies.factory.CellStrategyFactory.get_strategy")
    async def test_process_message_success(
        self,
        mock_get_strategy,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test successful message processing with real database."""
        # Mock strategy's process_cell_to_completion
        answer_data = TextAnswerData(
            type="text", value="This is a test answer from the AI."
        )
        mock_strategy = AsyncMock()

        # Mock load_cell_data to return proper structure with question_id
        mock_cell_data = AsyncMock()
        mock_cell_data.question.question_id = test_data["question"].id
        mock_strategy.load_cell_data.return_value = mock_cell_data

        mock_strategy.process_cell_to_completion.return_value = (
            AIAnswerSet.found([answer_data]),
            1,  # question_type_id
        )
        mock_get_strategy.return_value = mock_strategy

        # Mock successful lock acquisition
        mock_lock_provider.acquire_lock.return_value = "test_lock_token"
        mock_lock_provider.release_lock.return_value = True

        # Process message - services handle their own sessions
        await qa_worker.process_message(sample_message)

        # Verify external calls
        mock_strategy.process_cell_to_completion.assert_called_once_with(
            test_data["cell"].id, test_data["matrix"].company_id
        )
        mock_lock_provider.acquire_lock.assert_called_once()
        mock_lock_provider.release_lock.assert_called_once()

        # Verify database state using real services
        await test_db.refresh(test_data["cell"])
        await test_db.refresh(test_data["job"])
        assert test_data["cell"].status == MatrixCellStatus.COMPLETED.value
        assert (
            test_data["cell"].current_answer_set_id is not None
        )  # Should have a current answer
        assert test_data["job"].status == QAJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    @patch("packages.documents.services.document_service.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_process_message_missing_fields(
        self,
        mock_get_message_queue,
        mock_get_storage,
        qa_worker,
        test_db,
        mock_storage,
        mock_message_queue,
    ):
        """Test processing message with missing fields."""
        # Use common fixtures
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue.return_value = mock_message_queue

        incomplete_message = {"job_id": 1}  # Missing other required fields

        # ValidationError will be raised when BaseWorker tries to parse the message
        with pytest.raises(ValidationError):
            # We need to simulate what base_worker does - try to create the message object
            QAJobMessage(**incomplete_message)

    @patch("common.providers.storage.factory.get_storage")
    def test_worker_initialization(self, mock_storage_factory):
        """Test QAWorker initialization."""
        # Mock storage to prevent S3 connection
        mock_storage_factory.return_value = AsyncMock()

        worker = QAWorker()

        assert worker.queue_name == QueueName.QA_WORKER
        assert worker.worker_id.startswith(f"{QueueName.QA_WORKER}_worker_")
        assert worker.lock_provider is not None

    @patch("common.providers.storage.factory.get_storage")
    def test_worker_initialization_with_lock_provider(
        self, mock_storage_factory, mock_lock_provider
    ):
        """Test QAWorker initialization with custom lock provider."""
        # Mock storage to prevent S3 connection
        mock_storage_factory.return_value = AsyncMock()

        worker = QAWorker()
        worker.lock_provider = mock_lock_provider

        assert worker.queue_name == QueueName.QA_WORKER
        assert worker.worker_id.startswith(f"{QueueName.QA_WORKER}_worker_")
        assert worker.lock_provider is mock_lock_provider

    @pytest.mark.asyncio
    @patch("packages.matrices.strategies.factory.CellStrategyFactory.get_strategy")
    async def test_process_message_with_successful_locking(
        self,
        mock_get_strategy,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test message processing with successful lock acquisition."""
        # Mock strategy's process_cell_to_completion
        answer_data = TextAnswerData(
            type="text", value="This is a test answer from the AI."
        )
        mock_strategy = AsyncMock()

        # Mock load_cell_data to return proper structure with question_id
        mock_cell_data = AsyncMock()
        mock_cell_data.question.question_id = test_data["question"].id
        mock_strategy.load_cell_data.return_value = mock_cell_data

        mock_strategy.process_cell_to_completion.return_value = (
            AIAnswerSet.found([answer_data]),
            1,  # question_type_id
        )
        mock_get_strategy.return_value = mock_strategy

        # Mock successful lock acquisition
        mock_lock_provider.acquire_lock.return_value = "test_lock_token"
        mock_lock_provider.release_lock.return_value = True

        await qa_worker.process_message(sample_message)

        # Verify lock was acquired and released
        mock_lock_provider.acquire_lock.assert_called_once_with(
            f"matrix_cell:{test_data['cell'].id}", timeout_seconds=300
        )
        mock_lock_provider.release_lock.assert_called_once_with(
            f"matrix_cell:{test_data['cell'].id}", "test_lock_token"
        )

        # Verify strategy was called
        mock_strategy.process_cell_to_completion.assert_called_once_with(
            test_data["cell"].id, test_data["matrix"].company_id
        )

        # Verify database state using real services
        await test_db.refresh(test_data["cell"])
        await test_db.refresh(test_data["job"])
        assert test_data["cell"].status == MatrixCellStatus.COMPLETED.value
        assert (
            test_data["cell"].current_answer_set_id is not None
        )  # Should have a current answer
        assert test_data["job"].status == QAJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_process_message_lock_acquisition_failed(
        self,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test message processing when lock acquisition fails."""
        # Mock failed lock acquisition
        mock_lock_provider.acquire_lock.return_value = None

        await qa_worker.process_message(sample_message)

        # Verify lock acquisition was attempted
        mock_lock_provider.acquire_lock.assert_called_once_with(
            f"matrix_cell:{test_data['cell'].id}", timeout_seconds=300
        )

        # Verify job was marked as completed (not failed)
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == QAJobStatus.COMPLETED.value
        assert "another worker" in test_data["job"].error_message.lower()

    @pytest.mark.asyncio
    async def test_process_message_already_completed_with_lock(
        self,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test processing when cell is already completed (with lock held)."""
        # Create an answer first using matrix service
        matrix_service = MatrixService()
        answer_data = TextAnswerData(type="text", value="Already completed answer")
        ai_answer_set = AIAnswerSet.found([answer_data])
        await matrix_service.create_matrix_cell_answer_set_from_ai(
            test_data["cell"].id,
            1,  # SHORT_ANSWER question type
            ai_answer_set,
            set_as_current=True,
        )

        # Mark cell as completed
        test_data["cell"].status = MatrixCellStatus.COMPLETED.value
        await test_db.commit()

        # Mock successful lock acquisition
        mock_lock_provider.acquire_lock.return_value = "test_lock_token"
        mock_lock_provider.release_lock.return_value = True

        await qa_worker.process_message(sample_message)

        # Verify lock was acquired and released
        mock_lock_provider.acquire_lock.assert_called_once()
        mock_lock_provider.release_lock.assert_called_once()

        # Verify job was marked as completed
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == QAJobStatus.COMPLETED.value
        assert "already completed" in test_data["job"].error_message.lower()

    @pytest.mark.asyncio
    @patch("packages.matrices.strategies.factory.CellStrategyFactory.get_strategy")
    async def test_process_message_lock_released_on_exception(
        self,
        mock_get_strategy,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test that lock is released even when processing fails."""
        # Mock strategy to raise an exception
        mock_strategy = AsyncMock()

        # Mock load_cell_data to return proper structure with question_id
        mock_cell_data = AsyncMock()
        mock_cell_data.question.question_id = test_data["question"].id
        mock_strategy.load_cell_data.return_value = mock_cell_data

        mock_strategy.process_cell_to_completion.side_effect = Exception(
            "Strategy processing failed"
        )
        mock_get_strategy.return_value = mock_strategy

        # Mock successful lock acquisition
        mock_lock_provider.acquire_lock.return_value = "test_lock_token"
        mock_lock_provider.release_lock.return_value = True

        with pytest.raises(Exception, match="Strategy processing failed"):
            await qa_worker.process_message(sample_message)

        # Verify lock was acquired and released despite the exception
        mock_lock_provider.acquire_lock.assert_called_once()
        mock_lock_provider.release_lock.assert_called_once_with(
            f"matrix_cell:{test_data['cell'].id}", "test_lock_token"
        )

    @pytest.mark.asyncio
    @patch("packages.matrices.strategies.factory.CellStrategyFactory.get_strategy")
    async def test_process_message_handles_strategy_failure(
        self,
        mock_get_strategy,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test processing when strategy processing fails."""
        # Mock strategy to fail
        mock_strategy = AsyncMock()

        # Mock load_cell_data to return proper structure with question_id
        mock_cell_data = AsyncMock()
        mock_cell_data.question.question_id = test_data["question"].id
        mock_strategy.load_cell_data.return_value = mock_cell_data

        mock_strategy.process_cell_to_completion.side_effect = Exception(
            "Strategy processing failed"
        )
        mock_get_strategy.return_value = mock_strategy

        # Mock successful lock acquisition
        mock_lock_provider.acquire_lock.return_value = "test_lock_token"
        mock_lock_provider.release_lock.return_value = True

        with pytest.raises(Exception, match="Strategy processing failed"):
            await qa_worker.process_message(sample_message)

        # Verify lock was acquired and released
        mock_lock_provider.acquire_lock.assert_called_once()
        mock_lock_provider.release_lock.assert_called_once()

        # Verify job and cell were marked as failed using real database
        await test_db.refresh(test_data["job"])
        await test_db.refresh(test_data["cell"])
        assert test_data["job"].status == QAJobStatus.FAILED.value
        assert test_data["cell"].status == MatrixCellStatus.FAILED.value
        assert "Strategy processing failed" in test_data["job"].error_message

    @pytest.mark.asyncio
    async def test_process_message_handles_nonexistent_matrix_cell(
        self,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
    ):
        """Test processing when matrix cell doesn't exist."""
        # Mock successful lock acquisition
        mock_lock_provider.acquire_lock.return_value = "test_lock_token"
        mock_lock_provider.release_lock.return_value = True

        # Message with non-existent matrix cell ID
        invalid_message = QAJobMessage(
            job_id=test_data["job"].id,
            matrix_cell_id=99999,  # Non-existent
        )

        await qa_worker.process_message(invalid_message)

        # Verify lock was acquired and released
        mock_lock_provider.acquire_lock.assert_called_once()
        mock_lock_provider.release_lock.assert_called_once()

        # Verify job was marked as failed (cell not found)
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == QAJobStatus.FAILED.value
        assert "Matrix cell not found" in test_data["job"].error_message

    @pytest.mark.asyncio
    async def test_process_message_concurrent_lock_race_condition(
        self,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test that lock race conditions are handled properly."""
        # Simulate that lock acquisition fails (another worker got it)
        mock_lock_provider.acquire_lock.return_value = None

        await qa_worker.process_message(sample_message)

        # Verify lock acquisition was attempted
        mock_lock_provider.acquire_lock.assert_called_once_with(
            f"matrix_cell:{test_data['cell'].id}", timeout_seconds=300
        )

        # Verify job was marked as completed with appropriate message
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == QAJobStatus.COMPLETED.value
        assert "another worker" in test_data["job"].error_message.lower()

    @pytest.mark.asyncio
    async def test_process_message_idempotency_with_multiple_workers(
        self,
        qa_worker,
        mock_lock_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test that multiple workers processing the same cell handle idempotency correctly."""
        # Create an answer first using matrix service
        matrix_service = MatrixService()
        answer_data = TextAnswerData(type="text", value="First worker completed this")
        ai_answer_set = AIAnswerSet.found([answer_data])
        await matrix_service.create_matrix_cell_answer_set_from_ai(
            test_data["cell"].id,
            1,  # SHORT_ANSWER question type
            ai_answer_set,
            set_as_current=True,
        )

        # Mark cell as completed
        test_data["cell"].status = MatrixCellStatus.COMPLETED.value
        await test_db.commit()

        # Mock successful lock acquisition (second worker gets the lock)
        mock_lock_provider.acquire_lock.return_value = "test_lock_token"
        mock_lock_provider.release_lock.return_value = True

        await qa_worker.process_message(sample_message)

        # Verify lock was acquired and released
        mock_lock_provider.acquire_lock.assert_called_once()
        mock_lock_provider.release_lock.assert_called_once()

        # Verify job was marked as completed
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == QAJobStatus.COMPLETED.value
        assert "already completed" in test_data["job"].error_message.lower()
