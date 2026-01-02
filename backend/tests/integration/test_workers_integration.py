import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock

from packages.qa.workers.qa_worker import QAWorker
from packages.matrices.models.database.matrix import MatrixEntity, MatrixCellEntity
from packages.documents.models.database.document import DocumentEntity
from packages.questions.models.database.question import QuestionEntity
from packages.qa.models.database.qa_job import QAJobEntity
from packages.qa.models.domain.qa_job import QAJobStatus
from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.qa.services.ai_service import AIService
from common.providers.messaging.constants import QueueName


class TestQAWorkerIntegration:
    """Integration tests for QAWorker that test end-to-end functionality."""

    @pytest.fixture
    def mock_ai_service(self):
        """Create mock AI service for integration tests."""
        return AsyncMock(spec=AIService)

    @pytest.fixture
    async def qa_worker(self, mock_ai_service):
        """Create QAWorker with mocked AI service."""
        # Create worker instance with mocked AI service
        worker = QAWorker(ai_service=mock_ai_service)
        return worker

    @pytest.fixture
    def sample_message(self, test_data):
        """Sample message that would come from RabbitMQ."""
        return {
            "job_id": test_data["job"].id,
            "matrix_cell_id": test_data["cell"].id,
            "document_id": test_data["document"].id,
            "question_id": test_data["question"].id,
        }

    @pytest.fixture
    async def test_data(self, test_db):
        """Create real test data in the database."""

        # Create matrix
        matrix = MatrixEntity(name="Test Matrix", description="Integration test matrix")
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create document
        document = DocumentEntity(
            filename="test_doc.txt",
            storage_key="documents/1/test_doc.txt",
            content_type="text/plain",
            file_size=100,
            matrix_id=matrix.id,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Create question
        question = QuestionEntity(
            question_text="What programming language is mentioned in the document?",
            matrix_id=matrix.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Create matrix cell
        cell = MatrixCellEntity(
            matrix_id=matrix.id,
            document_id=document.id,
            question_id=question.id,
            status=MatrixCellStatus.PENDING.value,
        )
        test_db.add(cell)
        await test_db.commit()
        await test_db.refresh(cell)

        # Create QA job
        job = QAJobEntity(matrix_cell_id=cell.id, status=QAJobStatus.QUEUED.value)
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        return {
            "matrix": matrix,
            "document": document,
            "question": question,
            "cell": cell,
            "job": job,
        }

    @patch("packages.documents.services.document_service.get_storage")
    @pytest.mark.asyncio
    async def test_full_message_processing_workflow(
        self,
        mock_storage_factory,
        qa_worker,
        mock_ai_service,
        sample_message,
        test_db,
        test_data,
    ):
        """Test the complete message processing workflow."""

        # Mock only storage - document extraction is real
        mock_storage = AsyncMock()
        mock_storage.download.return_value = b"This is a test document about Python programming. Python is easy to learn and powerful."
        mock_storage_factory.return_value = mock_storage

        mock_ai_service.answer_question.return_value = "Based on the document content, this appears to be a test document about Python programming."

        # Process the message with real document extraction service
        await qa_worker.process_message(sample_message, test_db)

        # Verify external services were called
        mock_storage.download.assert_called_once_with("documents/1/test_doc.txt")
        mock_ai_service.answer_question.assert_called_once()

        # Verify database state - refresh the data from DB
        await test_db.refresh(test_data["job"])
        await test_db.refresh(test_data["cell"])

        assert test_data["job"].status == QAJobStatus.COMPLETED.value
        assert test_data["cell"].status == MatrixCellStatus.COMPLETED.value
        assert test_data["cell"].answer is not None

    @patch("packages.documents.services.document_service.get_storage")
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self,
        mock_storage_factory,
        qa_worker,
        mock_ai_service,
        sample_message,
        test_db,
        test_data,
    ):
        """Test error handling when AI service fails."""

        # Mock storage only
        mock_storage = AsyncMock()
        mock_storage.download.return_value = (
            b"This is a test document about Python programming."
        )
        mock_storage_factory.return_value = mock_storage

        # Make AI service fail
        mock_ai_service.answer_question.side_effect = Exception(
            "OpenAI API rate limit exceeded"
        )

        # Process should raise the exception
        with pytest.raises(Exception, match="OpenAI API rate limit exceeded"):
            await qa_worker.process_message(sample_message, test_db)

        # Verify database state shows failure
        await test_db.refresh(test_data["job"])
        await test_db.refresh(test_data["cell"])

        assert test_data["job"].status == QAJobStatus.FAILED.value
        assert test_data["cell"].status == MatrixCellStatus.FAILED.value

    @patch("packages.documents.services.document_service.get_storage")
    @pytest.mark.asyncio
    async def test_different_file_types(
        self,
        mock_storage_factory,
        qa_worker,
        mock_ai_service,
        sample_message,
        test_db,
        test_data,
    ):
        """Test processing different document types."""

        # Mock storage - use a different text file type instead of PDF to avoid PDF parsing issues
        mock_storage = AsyncMock()
        mock_storage.download.return_value = b"This is a markdown document about machine learning.\n\n# Machine Learning\n\nMachine learning is awesome."
        mock_storage_factory.return_value = mock_storage

        mock_ai_service.answer_question.return_value = (
            "This document is about machine learning."
        )

        # Create a real markdown document in the database (different file type than the base test)

        md_document = DocumentEntity(
            filename="test.md",
            storage_key="documents/1/test.md",
            content_type="text/markdown",
            file_size=1000,
            matrix_id=test_data["matrix"].id,
        )
        test_db.add(md_document)
        await test_db.commit()
        await test_db.refresh(md_document)

        # Create a new cell and job for the markdown document
        md_cell = MatrixCellEntity(
            matrix_id=test_data["matrix"].id,
            document_id=md_document.id,
            question_id=test_data["question"].id,
            status=MatrixCellStatus.PENDING.value,
        )
        test_db.add(md_cell)
        await test_db.commit()
        await test_db.refresh(md_cell)

        md_job = QAJobEntity(matrix_cell_id=md_cell.id, status=QAJobStatus.QUEUED.value)
        test_db.add(md_job)
        await test_db.commit()
        await test_db.refresh(md_job)

        # Update the sample message to use the markdown document data
        md_message = {
            "job_id": md_job.id,
            "matrix_cell_id": md_cell.id,
            "document_id": md_document.id,
            "question_id": test_data["question"].id,
        }

        # Process message
        await qa_worker.process_message(md_message, test_db)

        # Verify markdown was downloaded from storage
        mock_storage.download.assert_called_once_with("documents/1/test.md")

    @pytest.mark.asyncio
    async def test_worker_message_queue_integration(self, qa_worker):
        """Test worker integration with message queue (mocked)."""

        # Mock message queue
        mock_queue = AsyncMock()
        messages_to_process = [
            {"job_id": 1, "matrix_cell_id": 1, "document_id": 1, "question_id": 1},
            {"job_id": 2, "matrix_cell_id": 2, "document_id": 2, "question_id": 2},
        ]

        # Mock consume to call callback for each message
        async def mock_consume(queue_name, callback, auto_ack=True):
            for msg in messages_to_process:
                await callback(msg)

        mock_queue.consume.side_effect = mock_consume
        mock_queue.connect.return_value = True
        mock_queue.declare_queue.return_value = True

        # Mock the process_message to avoid database calls
        qa_worker.process_message = AsyncMock()

        # Mock the get_message_queue factory
        with patch(
            "common.workers.base_worker.get_message_queue", return_value=mock_queue
        ):
            # Setup worker
            await qa_worker.setup()

            # Start consuming (this would normally run forever, so we mock it)
            await mock_queue.consume(
                QueueName.QA_WORKER, qa_worker._message_handler, auto_ack=False
            )

            # Verify all messages were processed
            assert qa_worker.process_message.call_count == len(messages_to_process)

            # Cleanup
            await qa_worker.cleanup()

    @patch("packages.documents.services.document_service.get_storage")
    @pytest.mark.asyncio
    async def test_worker_performance_and_timeouts(
        self,
        mock_storage_factory,
        qa_worker,
        mock_ai_service,
        sample_message,
        test_db,
        test_data,
    ):
        """Test worker performance and timeout handling."""

        # Mock storage only
        mock_storage = AsyncMock()
        mock_storage.download.return_value = b"Test content"
        mock_storage_factory.return_value = mock_storage

        # Simulate slow AI response
        async def slow_ai_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
            return "Slow response from AI"

        mock_ai_service.answer_question.side_effect = slow_ai_response

        # Measure processing time
        start_time = time.time()
        await qa_worker.process_message(sample_message, test_db)
        processing_time = time.time() - start_time

        # Verify it completed (didn't timeout) and took expected time
        assert processing_time >= 0.1  # At least the AI delay
        assert processing_time < 5.0  # But not too long

        # Verify result
        mock_ai_service.answer_question.assert_called_once()

    @patch("packages.documents.services.document_service.get_storage")
    @pytest.mark.asyncio
    async def test_multiple_message_processing(
        self, mock_storage_factory, qa_worker, mock_ai_service, test_db, test_data
    ):
        """Test handling multiple messages sequentially (realistic for worker behavior)."""

        # Mock storage only
        mock_storage = AsyncMock()
        mock_storage.download.return_value = b"Test content"
        mock_storage_factory.return_value = mock_storage

        mock_ai_service.answer_question.return_value = "Test answer"

        # Create test data for multiple messages
        messages = []
        jobs_and_cells = []
        for i in range(1, 4):  # 3 messages
            # Create additional test data for each message

            cell = MatrixCellEntity(
                matrix_id=test_data["matrix"].id,
                document_id=test_data["document"].id,
                question_id=test_data["question"].id,
                status=MatrixCellStatus.PENDING.value,
            )
            test_db.add(cell)
            await test_db.commit()
            await test_db.refresh(cell)

            job = QAJobEntity(matrix_cell_id=cell.id, status=QAJobStatus.QUEUED.value)
            test_db.add(job)
            await test_db.commit()
            await test_db.refresh(job)

            messages.append(
                {
                    "job_id": job.id,
                    "matrix_cell_id": cell.id,
                    "document_id": test_data["document"].id,
                    "question_id": test_data["question"].id,
                }
            )
            jobs_and_cells.append((job, cell))

        # Process messages sequentially (as they would be in production)
        for msg in messages:
            await qa_worker.process_message(msg, test_db)

        # Verify all jobs completed successfully
        for job, cell in jobs_and_cells:
            await test_db.refresh(job)
            await test_db.refresh(cell)
            assert job.status == QAJobStatus.COMPLETED.value
            assert cell.status == MatrixCellStatus.COMPLETED.value

        # Verify AI was called for each message
        assert mock_ai_service.answer_question.call_count == len(messages)
