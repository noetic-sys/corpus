import json
import os
from deprecated import deprecated
from functools import lru_cache
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from common.providers.ai import get_ai_provider
from common.providers.ai.interface import AIProviderInterface
from common.providers.ai.models import InputMessage, MessageRole
from common.core.otel_axiom_exporter import trace_span, axiom_tracer, get_logger
from packages.ai_model.repositories.ai_model_repository import AIModelRepository
from packages.questions.models.domain.question import QuestionModel
from questions.question_type import QuestionTypeName
from ai_config import (
    get_ai_params,
    get_prompt_file,
    get_analysis_prompt_file,
)
from packages.matrices.models.domain.matrix_enums import MatrixType
from packages.qa.utils.message_builders import MessageBuilder, DocumentContext
from packages.qa.services.ai_response_parser import AIResponseParser
from packages.qa.models.domain.answer_data import AIAnswerSet
from packages.questions.services.question_option_service import QuestionOptionService

logger = get_logger(__name__)


class AIService:
    """Service that handles AI-related business logic using any AI provider."""

    def __init__(self, provider: AIProviderInterface, db_session: AsyncSession):

        self.provider = provider
        self.db_session = db_session
        # Navigate to project root and find prompts directory
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        self.prompts_dir = os.path.join(project_root, "prompts")
        self.question_option_service = QuestionOptionService()

    @trace_span
    @lru_cache(maxsize=100)
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt from a text file with memory caching."""
        with axiom_tracer.start_as_current_span("load_prompt"):
            filepath = os.path.join(self.prompts_dir, filename)
            with open(filepath, "r") as f:
                return f.read().strip()

    @trace_span
    async def answer_question(
        self,
        documents: List[DocumentContext],
        question: str,
        matrix_type: MatrixType,
        company_id: int,
        user_id: Optional[int] = None,
        question_id: Optional[int] = None,
        question_type_id: Optional[int] = None,
        min_answers: int = 1,
        max_answers: Optional[int] = 1,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIAnswerSet:
        """Generate a structured answer set to a question based on document content with type-specific formatting.

        Args:
            documents: List of DocumentContext objects (document_id + content pairs)
            question: The question text
            matrix_type: Type of matrix (determines analysis prompt)
            company_id: Company ID for quota/usage tracking
            user_id: Optional user ID for usage tracking
            question_id: Optional question ID for loading options
            question_type_id: Type ID for question formatting
            min_answers: Minimum number of answers required
            max_answers: Maximum number of answers allowed
            context: Optional additional context

        Returns:
            AIAnswerSet with answers
        """
        try:
            # Convert ID to enum
            type_enum = (
                QuestionTypeName.from_id(question_type_id) if question_type_id else None
            )

            logger.info(
                f"Processing question with {len(documents)} document(s), matrix_type: {matrix_type.value}, question_type: {type_enum.name if type_enum else 'DEFAULT'}, min_answers: {min_answers}, max_answers: {max_answers}"
            )

            # Load TWO system prompts:
            # 1. Analysis prompt (based on matrix type)
            analysis_prompt_file = get_analysis_prompt_file(matrix_type)
            logger.info(f"Loading analysis prompt from: {analysis_prompt_file}")
            analysis_prompt = self._load_prompt(analysis_prompt_file)

            # 2. Answer format prompt (based on question type)
            answer_format_file = (
                get_prompt_file(type_enum)
                if type_enum
                else get_prompt_file(QuestionTypeName.SHORT_ANSWER)
            )
            logger.info(f"Loading answer format prompt from: {answer_format_file}")
            answer_format_prompt = self._load_prompt(answer_format_file)

            # Get options for select questions
            options = (
                await self._get_question_options(question_id)
                if type_enum == QuestionTypeName.SELECT
                else []
            )
            if type_enum == QuestionTypeName.SELECT:
                logger.info(
                    f"Loaded {len(options)} options for SELECT question: {options}"
                )

            # Build structured messages optimized for caching
            user_messages = MessageBuilder.build_user_message(
                documents, question, type_enum, options, min_answers, max_answers
            )
            logger.info(
                f"Built structured messages with answer constraints: min={min_answers}, max={max_answers if max_answers is not None else 'unlimited'}"
            )

            # Get AI parameters based on question type
            ai_params = (
                get_ai_params(type_enum)
                if type_enum
                else get_ai_params(QuestionTypeName.SHORT_ANSWER)
            )

            # Combine BOTH system prompts into a single system message
            # (aisuite only supports one system message, extracts the first one)
            # Message order optimized for prompt caching:
            # 1. Combined system prompt (analysis + answer format)
            # 2. User messages (documents + question)
            combined_system_prompt = f"{analysis_prompt}\n\n{answer_format_prompt}"
            all_messages = [
                InputMessage(role=MessageRole.SYSTEM, content=combined_system_prompt),
            ] + user_messages

            # Log truncated messages for debugging
            logger.info(f"Sending {len(all_messages)} messages to AI:")
            for i, msg in enumerate(all_messages):
                truncated = (
                    msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                )
                logger.info(f"  [{i+1}] {msg.role.value}: {truncated}")

            response_message = await self.provider.send_messages(
                messages=all_messages,
                temperature=ai_params.temperature,
                max_tokens=ai_params.max_tokens,
            )

            response = response_message.content
            logger.info(f"Received AI response:")
            logger.info(f"{response}")

            # Parse AI response using new XML parser - now returns AIAnswerSet
            answer_set = AIResponseParser.parse_response(response, type_enum, options)
            logger.info(
                f"Parsed response into answer set: found={answer_set.answer_found}, count={answer_set.answer_count}"
            )

            logger.info(
                f"Generated answer set with {answer_set.answer_count} answer(s), found={answer_set.answer_found} for {type_enum.name if type_enum else 'standard'} question: {question[:50]}..."
            )
            return answer_set

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise Exception(f"Failed to generate answer: {str(e)}")

    async def _get_question_options(self, question_id: Optional[int]) -> List[str]:
        """Get options for a question from the database."""
        if not question_id:
            return []

        options = await self.question_option_service.get_options_for_question(
            question_id
        )
        return [option.value for option in options]

    @deprecated
    @trace_span
    async def summarize_document(self, document_content: str) -> str:
        """Generate a summary of the document content."""
        try:
            system_prompt = self._load_prompt("summarize_document.txt")
            user_message = f"""Please provide a concise summary of the following document:

{document_content}"""

            response = await self.provider.send_message(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                max_tokens=500,
            )

            logger.info("Generated document summary")
            return response

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            raise Exception(f"Failed to generate summary: {str(e)}")

    @deprecated
    @trace_span
    async def extract_key_information(
        self, document_content: str, info_type: str = "general"
    ) -> Dict[str, Any]:
        """Extract key information from document content."""
        try:
            system_prompt = self._load_prompt("extract_key_info.txt")
            user_message = f"""Extract key information from this document (focus on {info_type} information):

{document_content}

Please return a JSON object with the extracted information."""

            response = await self.provider.send_message(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.1,
                max_tokens=800,
            )

            # Try to parse as JSON, fallback to text if it fails
            try:
                key_info = json.loads(response)
            except json.JSONDecodeError:
                key_info = {"extracted_text": response}

            logger.info(f"Extracted key information of type: {info_type}")
            return key_info

        except Exception as e:
            logger.error(f"Error extracting key information: {e}")
            raise Exception(f"Failed to extract key information: {str(e)}")


@deprecated
def get_ai_service(
    db_session: AsyncSession,
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AIService:
    """Get AI service instance with specified provider and model."""
    provider = get_ai_provider(provider_type, model_name)
    return AIService(provider, db_session)


async def get_ai_service_for_question(
    db_session: AsyncSession,
    question: QuestionModel,
    ai_config_override: Optional[dict] = None,
) -> AIService:
    """Get AI service instance configured for a specific question."""

    # If question has a specific AI model configured, use it
    if question.ai_model_id:
        ai_model_repo = AIModelRepository()
        ai_model = await ai_model_repo.get_with_provider(question.ai_model_id)

        if (
            ai_model
            and ai_model.enabled
            and ai_model.provider
            and ai_model.provider.enabled
        ):
            provider_type = ai_model.provider.name
            model_name = ai_model.model_name

            # Create provider with specific model
            provider = get_ai_provider(provider_type, model_name)
            return AIService(provider, db_session)

    # Use global default
    provider = get_ai_provider()
    return AIService(provider, db_session)
