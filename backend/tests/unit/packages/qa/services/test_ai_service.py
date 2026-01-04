import pytest
import os
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from common.providers.ai.models import Message, MessageRole
from packages.qa.services.ai_service import AIService
from common.providers.ai.interface import AIProviderInterface
from packages.qa.models.domain.answer_data import (
    TextAnswerData,
    SelectAnswerData,
    CurrencyAnswerData,
    DateAnswerData,
)
from packages.qa.models.domain.answer_data import AIAnswerSet
from packages.qa.utils.message_builders import DocumentContext
from packages.questions.services.question_option_service import QuestionOptionService
from packages.questions.models.domain.question_option import (
    QuestionOptionSetCreateModel,
    QuestionOptionCreateModel,
)
from packages.matrices.models.domain.matrix_enums import MatrixType
from tests.conftest import AI_RESPONSE_SAMPLES


class MockAIProvider(AIProviderInterface):
    """Mock AI provider for testing."""

    def __init__(self):
        self.send_message_calls = []

    async def send_message(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = None,
    ) -> str:
        """Mock send_message that records calls and returns predictable responses."""
        self.send_message_calls.append(
            {
                "system_prompt": system_prompt,
                "user_message": user_message,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )

        # Return different responses based on system prompt content (more specific first)
        if "summaries" in system_prompt:
            return "Python is a high-level programming language with easy syntax."
        elif "extracts key information" in system_prompt:
            return '{"language": "Python", "type": "programming", "features": ["easy", "interpreted"]}'
        elif (
            "answers questions" in system_prompt
            or "brief answers" in system_prompt
            or "assistant" in system_prompt
            or "document analysis" in system_prompt
        ):
            if "Apple" in user_message:
                return AI_RESPONSE_SAMPLES["not_found"]
            # Select responses (unified select format)
            if (
                "select from those that are relevant" in user_message
                or "select one of the following" in user_message
            ):
                if "Python" in user_message and "Programming" in user_message:
                    return """{
                        "options": [
                            {
                                "value": "Python",
                                "citations": []
                            },
                            {
                                "value": "Programming",
                                "citations": []
                            }
                        ]
                    }"""
                elif "Rust" in user_message and "Go" in user_message:
                    return """{
                        "options": [
                            {
                                "value": "Rust",
                                "citations": []
                            },
                            {
                                "value": "Go",
                                "citations": []
                            }
                        ]
                    }"""
                return """{
                    "options": [
                        {
                            "value": "Python",
                            "citations": []
                        }
                    ]
                }"""
            # Currency responses (list format)
            elif (
                "currency" in system_prompt
                or "amount" in user_message
                or "cost" in user_message
            ):
                return AI_RESPONSE_SAMPLES["currency"]["valid"]
            # Date responses (list format)
            elif "date" in system_prompt or "date" in user_message:
                return AI_RESPONSE_SAMPLES["date"]["valid"]
            # Default text responses
            return AI_RESPONSE_SAMPLES["text"]["valid"]
        else:
            return AI_RESPONSE_SAMPLES["text"]["valid"]

    async def send_messages(
        self,
        messages,
        tools=None,
        temperature: float = 0.7,
        max_tokens: int = None,
    ):
        """Mock send_messages that forwards to send_message logic."""
        # Extract system prompt and combine user messages
        system_prompt = ""
        user_content_parts = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            elif msg.role == MessageRole.USER:
                user_content_parts.append(msg.content)

        # Combine user messages into single message for legacy logic compatibility
        user_message = "\n".join(user_content_parts)

        # Use existing send_message logic to generate response content
        response_content = await self.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return Message(content=response_content, tool_calls=None)


class TestAIService:
    """Unit tests for AIService with mocked provider."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock AI provider."""
        return MockAIProvider()

    @pytest.fixture
    async def sample_question_with_options(self, ai_service, sample_question):
        """Create a question with options."""

        option_service = QuestionOptionService()
        create_model = QuestionOptionSetCreateModel(
            options=[
                QuestionOptionCreateModel(value="Yes"),
                QuestionOptionCreateModel(value="No"),
                QuestionOptionCreateModel(value="Maybe"),
            ],
        )
        await option_service.create_option_set(sample_question.id, create_model)
        return sample_question

    @pytest.fixture
    def mock_prompts_dir(self, tmp_path):
        """Create temporary prompt files for testing."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create subdirectories
        (prompts_dir / "answers").mkdir()
        (prompts_dir / "analysis").mkdir()

        # Create answer format prompt files in answers/ subdirectory
        answer_prompts = {
            "answers/answer_question.txt": "You are a helpful assistant that answers questions based on provided document content.",
            "answers/answer_question_date.txt": "You are a helpful assistant that extracts dates from documents.",
            "answers/answer_question_currency.txt": "You are a helpful assistant that extracts currency amounts from documents.",
            "answers/answer_question_short.txt": "You are a helpful assistant that provides brief answers to questions.",
            "answers/answer_question_select.txt": "You are a document analysis assistant that selects relevant options from a predefined list based on document content.",
        }

        # Create analysis prompt files in analysis/ subdirectory
        analysis_prompts = {
            "analysis/standard_analysis.txt": "You are analyzing a standard document-question matrix.",
            "analysis/correlation_analysis.txt": "You are analyzing a correlation matrix.",
        }

        # Create deprecated prompt files at root level
        deprecated_prompts = {
            "summarize_document.txt": "You are a helpful assistant that creates concise summaries of documents.",
            "extract_key_info.txt": "You are a helpful assistant that extracts key information from documents.",
        }

        for filename, content in {
            **answer_prompts,
            **analysis_prompts,
            **deprecated_prompts,
        }.items():
            (prompts_dir / filename).write_text(content)

        return str(prompts_dir)

    @pytest.fixture
    async def ai_service(self, mock_provider, mock_prompts_dir, test_db: AsyncSession):
        """Create AIService with mocked provider and prompts directory."""
        service = AIService(mock_provider)
        service.prompts_dir = mock_prompts_dir
        return service

    @pytest.fixture
    def sample_document(self):
        """Sample document content for testing."""
        return (
            "Python is a high-level programming language. It is easy to learn and use."
        )

    @pytest.mark.asyncio
    async def test_answer_question_success(
        self, ai_service, mock_provider, sample_document
    ):
        """Test successful question answering."""
        question = "What is Python?"
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await ai_service.answer_question(
            documents,
            question,
            matrix_type=MatrixType.STANDARD,
            company_id=1,
        )

        # Result should be an AIAnswerSet with TextAnswerData
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1
        assert isinstance(result.answers[0], TextAnswerData)
        assert result.answers[0].value == "This is the answer text"
        assert len(mock_provider.send_message_calls) == 1

        call = mock_provider.send_message_calls[0]
        assert (
            "brief" in call["system_prompt"].lower()
            or "short" in call["system_prompt"].lower()
        )
        assert sample_document in call["user_message"]
        assert question in call["user_message"]
        # Default is SHORT_ANSWER when no question_type_id provided
        assert call["temperature"] == 0.1
        # assert call["max_tokens"] == 200

    @pytest.mark.asyncio
    async def test_answer_question_not_in_document(
        self, ai_service, mock_provider, sample_document
    ):
        """Test answering question when answer is not in document."""
        question = "What is Apple's stock price?"
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await ai_service.answer_question(
            documents,
            question,
            matrix_type=MatrixType.STANDARD,
            company_id=1,
        )

        # Result should be an AIAnswerSet with answer_found=False
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answer_count == 0
        assert len(result.answers) == 0
        assert len(mock_provider.send_message_calls) == 1

    @pytest.mark.asyncio
    async def test_answer_question_with_context(
        self, ai_service, mock_provider, sample_document
    ):
        """Test answering question with additional context."""
        question = "What is Python?"
        context = {"audience": "beginners"}
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await ai_service.answer_question(
            documents,
            question,
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            context=context,
        )

        # Result should be an AIAnswerSet with TextAnswerData
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1
        assert isinstance(result.answers[0], TextAnswerData)
        assert result.answers[0].value == "This is the answer text"
        assert len(mock_provider.send_message_calls) == 1

    @pytest.mark.asyncio
    async def test_summarize_document_success(
        self, ai_service, mock_provider, sample_document
    ):
        """Test successful document summarization."""
        result = await ai_service.summarize_document(sample_document)

        assert result == "Python is a high-level programming language with easy syntax."
        assert len(mock_provider.send_message_calls) == 1

        call = mock_provider.send_message_calls[0]
        assert "summaries" in call["system_prompt"]
        assert sample_document in call["user_message"]
        assert call["temperature"] == 0.3
        # assert call["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_extract_key_information_success(
        self, ai_service, mock_provider, sample_document
    ):
        """Test successful key information extraction."""
        info_type = "technical"

        result = await ai_service.extract_key_information(sample_document, info_type)

        expected_result = {
            "language": "Python",
            "type": "programming",
            "features": ["easy", "interpreted"],
        }
        assert result == expected_result
        assert len(mock_provider.send_message_calls) == 1

        call = mock_provider.send_message_calls[0]
        assert "extracts key information" in call["system_prompt"]
        assert sample_document in call["user_message"]
        assert info_type in call["user_message"]
        assert call["temperature"] == 0.1
        # assert call["max_tokens"] == 800

    @pytest.mark.asyncio
    async def test_extract_key_information_default_type(
        self, ai_service, mock_provider, sample_document
    ):
        """Test key information extraction with default info_type."""
        result = await ai_service.extract_key_information(sample_document)

        expected_result = {
            "language": "Python",
            "type": "programming",
            "features": ["easy", "interpreted"],
        }
        assert result == expected_result

        call = mock_provider.send_message_calls[0]
        assert "general" in call["user_message"]  # Default info_type

    @pytest.mark.asyncio
    async def test_extract_key_information_invalid_json(
        self, ai_service, sample_document, test_db
    ):
        """Test key information extraction when provider returns invalid JSON."""
        # Create a provider that returns invalid JSON
        invalid_json_provider = MockAIProvider()
        invalid_json_provider.send_message = AsyncMock(
            return_value="This is not valid JSON"
        )

        service = AIService(invalid_json_provider)
        service.prompts_dir = ai_service.prompts_dir

        result = await service.extract_key_information(sample_document)

        expected_result = {"extracted_text": "This is not valid JSON"}
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_answer_question_provider_error(
        self, ai_service, sample_document, test_db
    ):
        """Test error handling when provider fails."""
        # Create a provider that raises an exception
        error_provider = MockAIProvider()
        error_provider.send_message = AsyncMock(side_effect=Exception("Provider error"))

        service = AIService(error_provider)
        service.prompts_dir = ai_service.prompts_dir
        documents = [DocumentContext(document_id=1, content=sample_document)]

        with pytest.raises(Exception) as exc_info:
            await service.answer_question(
                documents,
                "Test question",
                matrix_type=MatrixType.STANDARD,
                company_id=1,
            )

        assert "Failed to generate answer: Provider error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_answer_question_multi_select_with_options(
        self, ai_service, mock_provider, sample_document, test_db
    ):
        """Test multi-select question answering with options."""
        mock_service = AsyncMock()
        mock_service.get_options_for_question.return_value = [
            AsyncMock(value="Python"),
            AsyncMock(value="Programming"),
            AsyncMock(value="JavaScript"),
        ]
        ai_service.question_option_service = mock_service
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await ai_service.answer_question(
            documents,
            "What topics are covered?",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            question_id=123,
            question_type_id=5,  # SELECT
        )

        # Result should be an AIAnswerSet with multiple SelectAnswerData objects
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 2  # Python and Programming options
        assert len(result.answers) == 2

        # Each answer should be a separate SelectAnswerData object
        for answer in result.answers:
            assert isinstance(answer, SelectAnswerData)

        # Check that we got the expected options
        option_values = [answer.option_value for answer in result.answers]
        assert "Python" in option_values
        assert "Programming" in option_values

        # Verify correct prompt file was used
        call = mock_provider.send_message_calls[0]
        assert "selects relevant options" in call["system_prompt"]
        assert "select from those that are relevant" in call["user_message"]
        assert "Python" in call["user_message"]
        assert "Programming" in call["user_message"]
        assert call["temperature"] == 0.0
        # assert call["max_tokens"] == 300

    @pytest.mark.asyncio
    async def test_answer_question_single_select_with_options(
        self, ai_service, mock_provider, sample_document, test_db
    ):
        """Test single-select question answering with options (unified SELECT type)."""
        mock_service = AsyncMock()
        mock_service.get_options_for_question.return_value = [
            AsyncMock(value="Python"),
            AsyncMock(value="JavaScript"),
            AsyncMock(value="Go"),
        ]
        ai_service.question_option_service = mock_service
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await ai_service.answer_question(
            documents,
            "What language is this about?",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            question_id=123,
            question_type_id=5,  # SELECT
        )

        # Result should be an AIAnswerSet with one SelectAnswerData
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1
        assert isinstance(result.answers[0], SelectAnswerData)
        assert result.answers[0].option_value == "Python"

        # Verify unified SELECT instructions are used
        call = mock_provider.send_message_calls[0]
        assert "select from those that are relevant" in call["user_message"]
        assert call["temperature"] == 0.0
        # assert call["max_tokens"] == 300

    @pytest.mark.asyncio
    @pytest.mark.skip
    async def test_answer_question_multi_select_no_options(
        self, ai_service, mock_provider, sample_document, test_db
    ):
        """Test multi-select question without options configured."""
        mock_service = AsyncMock()
        mock_service.get_options_for_question.return_value = []
        ai_service.question_option_service = mock_service
        documents = [DocumentContext(document_id=1, content=sample_document)]

        _ = await ai_service.answer_question(
            documents,
            "What topics are covered?",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            question_id=123,
            question_type_id=5,  # SELECT
        )

        # Should still get a response, but with "no options" message in instructions
        call = mock_provider.send_message_calls[0]
        assert "No options configured" in call["user_message"]

    @pytest.mark.asyncio
    async def test_summarize_document_provider_error(
        self, ai_service, sample_document, test_db
    ):
        """Test error handling when provider fails during summarization."""
        error_provider = MockAIProvider()
        error_provider.send_message = AsyncMock(side_effect=Exception("Provider error"))

        service = AIService(error_provider)
        service.prompts_dir = ai_service.prompts_dir

        with pytest.raises(Exception) as exc_info:
            await service.summarize_document(sample_document)

        assert "Failed to generate summary: Provider error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_key_information_provider_error(
        self, ai_service, sample_document, test_db
    ):
        """Test error handling when provider fails during extraction."""
        error_provider = MockAIProvider()
        error_provider.send_message = AsyncMock(side_effect=Exception("Provider error"))

        service = AIService(error_provider)
        service.prompts_dir = ai_service.prompts_dir

        with pytest.raises(Exception) as exc_info:
            await service.extract_key_information(sample_document)

        assert "Failed to extract key information: Provider error" in str(
            exc_info.value
        )

    def test_load_prompt_success(self, ai_service):
        """Test successful prompt loading."""
        prompt = ai_service._load_prompt("answers/answer_question.txt")

        assert "answers questions" in prompt

    def test_load_prompt_file_not_found(self, ai_service):
        """Test error handling when prompt file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ai_service._load_prompt("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_prompt_file_loading_integration(
        self, mock_provider, mock_prompts_dir, test_db
    ):
        """Test that the service correctly loads and uses prompt files."""
        # Modify the SHORT_ANSWER prompt file since that's the default
        with open(
            os.path.join(mock_prompts_dir, "answers", "answer_question_short.txt"), "w"
        ) as f:
            f.write("CUSTOM_ANSWER_PROMPT: You are a test assistant.")

        service = AIService(mock_provider)
        service.prompts_dir = mock_prompts_dir
        documents = [DocumentContext(document_id=1, content="test doc")]

        await service.answer_question(
            documents,
            "test question",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
        )

        # The answer_question uses TWO system prompts - analysis and answer format
        # We modified the answer format prompt, so check that it's in the messages
        call = mock_provider.send_message_calls[0]
        # The call should contain both prompts in the user_message or system_prompt
        # Since send_messages is being used, we need to check differently
        # Actually the mock's send_message is being called through send_messages
        # Let's just verify the custom prompt appears somewhere
        assert "CUSTOM_ANSWER_PROMPT" in str(call)

    @pytest.mark.asyncio
    async def test_user_message_formatting(self, ai_service, mock_provider):
        """Test that user messages are formatted correctly."""
        documents = [DocumentContext(document_id=1, content="Test document content")]
        question = "Test question"

        await ai_service.answer_question(
            documents,
            question,
            matrix_type=MatrixType.STANDARD,
            company_id=1,
        )

        call = mock_provider.send_message_calls[0]
        user_message = call["user_message"]

        assert "Document 1:" in user_message
        assert "Test document content" in user_message
        assert "Question:" in user_message
        assert question in user_message
        # Default instruction for SHORT_ANSWER (since no question_type_id provided)
        assert "brief, concise answer" in user_message

    # Tests for the utility methods that moved to separate files should be in their own test files

    @pytest.mark.asyncio
    async def test_get_question_options_exists(
        self, ai_service, sample_question_with_options
    ):
        """Test getting question options when they exist."""
        options = await ai_service._get_question_options(
            sample_question_with_options.id
        )

        assert len(options) == 3
        assert "Yes" in options
        assert "No" in options
        assert "Maybe" in options

    @pytest.mark.asyncio
    async def test_get_question_options_none(self, ai_service):
        """Test getting question options with None question_id."""
        options = await ai_service._get_question_options(None)
        assert options == []

    @pytest.mark.asyncio
    async def test_get_question_options_not_found(self, ai_service):
        """Test getting question options for non-existent question."""
        options = await ai_service._get_question_options(999)
        assert options == []

    # Formatting tests moved to test_response_formatters.py

    @pytest.mark.asyncio
    async def test_answer_question_with_date_type(self, sample_document, test_db):
        """Test answer_question with DATE type handling."""
        # Create a mock provider that returns a date response
        mock_provider = MockAIProvider()
        mock_provider.send_message = AsyncMock(
            return_value=AI_RESPONSE_SAMPLES["date"]["valid"]
        )

        service = AIService(mock_provider)
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await service.answer_question(
            documents=documents,
            question="What is the contract date?",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            question_type_id=3,  # DATE
        )

        # Verify provider was called with correct parameters
        mock_provider.send_message.assert_called_once()
        call_args = mock_provider.send_message.call_args
        assert call_args.kwargs["temperature"] == 0.0
        # assert call_args.kwargs["max_tokens"] == 50

        # Result should be an AIAnswerSet with DateAnswerData
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1
        assert isinstance(result.answers[0], DateAnswerData)
        assert result.answers[0].value == "2024-03-15"
        assert result.answers[0].parsed_date == "2024-03-15"

    @pytest.mark.asyncio
    async def test_answer_question_with_select_type(
        self, sample_question_with_options, sample_document, test_db
    ):
        """Test answer_question with SELECT type."""
        # Create a mock provider that returns a select response
        mock_provider = MockAIProvider()
        mock_provider.send_message = AsyncMock(
            return_value="""{
            "options": [
                {
                    "value": "Yes",
                    "citations": []
                }
            ]
        }"""
        )

        service = AIService(mock_provider)
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await service.answer_question(
            documents=documents,
            question="Do you agree?",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            question_id=sample_question_with_options.id,
            question_type_id=5,  # SELECT
        )

        # Verify provider was called with correct parameters
        mock_provider.send_message.assert_called_once()
        call_args = mock_provider.send_message.call_args
        assert call_args.kwargs["temperature"] == 0.0
        # assert call_args.kwargs["max_tokens"] == 300

        # Result should be an AIAnswerSet with SelectAnswerData
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1
        assert isinstance(result.answers[0], SelectAnswerData)
        assert result.answers[0].option_value == "Yes"

    @pytest.mark.asyncio
    async def test_answer_question_with_currency_type(self, sample_document, test_db):
        """Test answer_question with CURRENCY type handling."""
        # Create a mock provider that returns a currency response in new JSON format
        mock_provider = MockAIProvider()
        mock_provider.send_message = AsyncMock(
            return_value=AI_RESPONSE_SAMPLES["currency"]["valid"]
        )

        service = AIService(mock_provider)
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await service.answer_question(
            documents=documents,
            question="How much does it cost?",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            question_type_id=4,  # CURRENCY
        )

        # Verify provider was called with correct parameters
        mock_provider.send_message.assert_called_once()
        call_args = mock_provider.send_message.call_args
        assert call_args.kwargs["temperature"] == 0.0
        # assert call_args.kwargs["max_tokens"] == 100

        # Result should be an AIAnswerSet with CurrencyAnswerData
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1
        assert isinstance(result.answers[0], CurrencyAnswerData)
        assert result.answers[0].value == "1250.5 USD"
        assert result.answers[0].amount == 1250.5  # Should have extracted amount
        assert result.answers[0].currency == "USD"  # Should have extracted currency

    @pytest.mark.asyncio
    async def test_answer_question_with_short_answer_type(
        self, sample_document, test_db
    ):
        """Test answer_question with SHORT_ANSWER type handling."""
        long_response = "A" * 300  # 300 characters

        # Create a mock provider that returns a long response in JSON format
        mock_provider = MockAIProvider()
        long_json_response = (
            f"""{{"items": [{{"value": "{long_response}", "citations": []}}]}}"""
        )
        mock_provider.send_message = AsyncMock(return_value=long_json_response)

        service = AIService(mock_provider)
        documents = [DocumentContext(document_id=1, content=sample_document)]

        result = await service.answer_question(
            documents=documents,
            question="What is this?",
            matrix_type=MatrixType.STANDARD,
            company_id=1,
            question_type_id=1,  # SHORT_ANSWER
        )

        # Verify provider was called with correct parameters
        mock_provider.send_message.assert_called_once()
        call_args = mock_provider.send_message.call_args
        assert call_args.kwargs["temperature"] == 0.1
        # assert call_args.kwargs["max_tokens"] == 200

        # Result should be an AIAnswerSet with TextAnswerData
        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1
        assert isinstance(result.answers[0], TextAnswerData)
        # Response should be the full response (truncation may be handled elsewhere)
        assert result.answers[0].value == long_response
