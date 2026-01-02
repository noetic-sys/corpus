"""User message building utilities for AI service."""

from typing import List, Optional
from pydantic import BaseModel
from questions.question_type import QuestionTypeName
from ai_config import get_type_instruction
from common.providers.ai.models import InputMessage, MessageRole


class DocumentContext(BaseModel):
    """Document context for message building - pairs document ID with content."""

    document_id: int
    content: str


class MessageBuilder:
    """Builds user messages for AI service based on question type."""

    @staticmethod
    def build_user_message(
        documents: List[DocumentContext],
        question: str,
        question_type: Optional[QuestionTypeName] = None,
        options: Optional[List[str]] = None,
        min_answers: int = 1,
        max_answers: Optional[int] = 1,
    ) -> List[InputMessage]:
        """Build structured messages optimized for provider caching.

        Args:
            documents: List of DocumentContext (document_id + content pairs)
                For standard matrices: [DocumentContext(123, "content")]
                For correlation matrices: [DocumentContext(123, "content1"), DocumentContext(456, "content2")]
            question: The question text (may contain template variables like {{A}}, {{B}})
            question_type: Type of question for formatting instructions
            options: Options for SELECT type questions
            min_answers: Minimum number of answers required
            max_answers: Maximum number of answers allowed

        Returns:
            List of messages with separate messages for each document (optimal for caching)
            Uses document IDs as labels for template variable resolution
        """
        messages = []

        # Create separate message for EACH document (highly cacheable - reused across questions)
        for doc_context in documents:
            messages.append(
                InputMessage(
                    role=MessageRole.USER,
                    content=f"Document {doc_context.document_id}:\n{doc_context.content}",
                )
            )

        # Final message: Question with type-specific instructions (cacheable across docs)
        if not question_type:
            instruction = get_type_instruction(QuestionTypeName.SHORT_ANSWER)
        elif question_type == QuestionTypeName.SELECT:
            instruction = MessageBuilder._build_select_instructions(options or [])
        else:
            instruction = get_type_instruction(question_type)

        # Add answer count constraints
        constraint_text = MessageBuilder._build_answer_count_constraint_text(
            min_answers, max_answers
        )

        question_content = f"Question: {question}{instruction}{constraint_text}"

        messages.append(InputMessage(role=MessageRole.USER, content=question_content))

        return messages

    @staticmethod
    def _build_select_instructions(options: List[str]) -> str:
        """Build select question instructions with options (constraints handled separately)."""
        if not options:
            return "\n\nNo options configured for this question."

        options_text = ", ".join(f'"{opt}"' for opt in options)

        return f"\n\nFrom the following options, select from those that are relevant to, mentioned in, or related to the document content: {options_text}. \n\nBe inclusive - if an option relates to the document topic, theme, or content in any way, include it. Use the exact option text provided."

    @staticmethod
    def _build_answer_count_constraint_text(
        min_answers: int, max_answers: Optional[int]
    ) -> str:
        """Build answer count constraint text for any question type."""
        if max_answers is None:
            # Unlimited answers
            if min_answers == 1:
                return "\n\nProvide at least 1 answer (or more if found)."
            else:
                return f"\n\nProvide at least {min_answers} answers (or more if found)."
        elif min_answers == max_answers:
            # Exact number required
            if min_answers == 1:
                return "\n\nProvide exactly 1 answer."
            else:
                return f"\n\nProvide exactly {min_answers} answers."
        else:
            # Range of answers
            return f"\n\nProvide between {min_answers} and {max_answers} answers."
