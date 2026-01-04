"""
Agent-based QA service.

Uses Claude Agent SDK to selectively read document chunks and answer questions.
"""

import os
from functools import lru_cache
from typing import Optional, List

from common.core.otel_axiom_exporter import trace_span, get_logger
from ai_config import get_prompt_file, get_analysis_prompt_file
from packages.matrices.models.domain.matrix_enums import MatrixType
from questions.question_type import QuestionTypeName
from packages.qa.models.domain.answer_data import AIAnswerSet
from packages.questions.services.question_option_service import QuestionOptionService

logger = get_logger(__name__)


class AgentQAService:
    """Service for agent-based QA using chunk-based retrieval."""

    def __init__(self):
        """Initialize agent QA service."""
        # Set up prompts directory
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        self.prompts_dir = os.path.join(project_root, "prompts")
        self.question_option_service = QuestionOptionService()

    @lru_cache(maxsize=100)
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt from file with caching.

        Args:
            filename: Prompt filename relative to prompts directory

        Returns:
            Prompt content
        """
        filepath = os.path.join(self.prompts_dir, filename)
        with open(filepath, "r") as f:
            return f.read().strip()

    def _compose_agent_prompt(
        self,
        matrix_type: MatrixType,
        question_type: QuestionTypeName,
        question_text: str,
        document_ids: List[int],
        options: Optional[List[str]] = None,
        min_answers: int = 1,
        max_answers: Optional[int] = 1,
    ) -> str:
        """Compose mega-prompt from three components.

        Components:
        1. Agent orchestration (how to use chunk tools)
        2. Analysis style (standard vs correlation, citation requirements)
        3. Output format (short answer vs select, JSON structure)

        Args:
            matrix_type: Matrix type for analysis prompt
            question_type: Question type for output format
            question_text: The question to answer
            document_ids: List of available document IDs
            options: Options for SELECT questions
            min_answers: Minimum number of answers
            max_answers: Maximum number of answers

        Returns:
            Composed prompt string
        """
        logger.info(
            f"Composing agent prompt: matrix={matrix_type.value}, "
            f"question_type={question_type.name}, docs={len(document_ids)}"
        )

        # Part 1: Agent orchestration (chunk reading strategy)
        orchestration = self._load_prompt("qa_orchestrator.txt")

        # Part 2: Analysis style (citation requirements, document markers)
        analysis_file = get_analysis_prompt_file(matrix_type)
        analysis = self._load_prompt(analysis_file)

        # Part 3: Output format (JSON structure)
        output_file = get_prompt_file(question_type)
        output_format = self._load_prompt(output_file)

        # Part 4: Task context
        doc_list = ", ".join([f"[[document:{doc_id}]]" for doc_id in document_ids])

        task_context = f"""# YOUR TASK

**Question:** {question_text}

**Available Documents:** {doc_list}

**Document IDs for MCP tools:** {', '.join(str(d) for d in document_ids)}"""

        if question_type == QuestionTypeName.SELECT and options:
            options_list = "\n".join([f"  - {opt}" for opt in options])
            task_context += f"""

**Available Options (SELECT question):**
{options_list}

Select ONLY from these exact option texts."""

        # Add answer count constraints
        if max_answers is None:
            if min_answers == 1:
                task_context += "\n\nProvide at least 1 answer (or more if found)."
            else:
                task_context += (
                    f"\n\nProvide at least {min_answers} answers (or more if found)."
                )
        elif min_answers == max_answers:
            if min_answers == 1:
                task_context += "\n\nProvide exactly 1 answer."
            else:
                task_context += f"\n\nProvide exactly {min_answers} answers."
        else:
            task_context += (
                f"\n\nProvide between {min_answers} and {max_answers} answers."
            )

        # Compose mega-prompt
        composed = f"""{orchestration}

---

{analysis}

---

{output_format}

---

{task_context}

Begin by using the MCP tools to discover and read relevant chunks, then provide your answer in the required JSON format with proper [[cite:N]] citations and [[document:ID]] markers."""

        logger.info(f"Composed prompt: {len(composed)} characters")
        return composed

    @trace_span
    async def answer_question_with_agents(
        self,
        document_ids: List[int],
        question: str,
        matrix_type: MatrixType,
        question_id: Optional[int] = None,
        question_type_id: Optional[int] = None,
        min_answers: int = 1,
        max_answers: Optional[int] = 1,
    ) -> AIAnswerSet:
        """Answer a question using agent-based chunk retrieval.

        Uses Claude Agent SDK to:
        1. Discover available chunks via MCP tools
        2. Selectively read relevant chunks
        3. Synthesize answer with citations

        Args:
            document_ids: List of document IDs to query
            question: Question text
            matrix_type: Matrix type (for analysis prompt)
            question_id: Question ID (for loading options)
            question_type_id: Question type ID (for output format)
            min_answers: Minimum answers required
            max_answers: Maximum answers allowed

        Returns:
            AIAnswerSet with answers and citations
        """
        try:
            # Convert type ID to enum
            question_type = (
                QuestionTypeName.from_id(question_type_id)
                if question_type_id
                else QuestionTypeName.SHORT_ANSWER
            )

            logger.info(
                f"Agent QA: {len(document_ids)} docs, matrix={matrix_type.value}, "
                f"type={question_type.name}, min={min_answers}, max={max_answers}"
            )

            # Get options for SELECT questions
            options = []
            if question_type == QuestionTypeName.SELECT and question_id:
                options = await self._get_question_options(question_id)
                logger.info(f"Loaded {len(options)} options for SELECT question")

            # Compose mega-prompt
            agent_prompt = self._compose_agent_prompt(
                matrix_type=matrix_type,
                question_type=question_type,
                question_text=question,
                document_ids=document_ids,
                options=options,
                min_answers=min_answers,
                max_answers=max_answers,
            )

            # TODO: Execute agent with Claude Agent SDK
            # For now, raise not implemented
            raise NotImplementedError(
                "Agent execution not yet implemented. Need to integrate Claude Agent SDK."
            )

            # Future implementation:
            # from claude_agent_sdk import ClaudeSDKClient
            #
            # agent_options = {
            #     'allowed_tools': [
            #         'list_document_chunks',
            #         'read_document_chunk',
            #         'search_document_chunks',
            #         'hybrid_search_chunks',  # NEW: Hybrid BM25 + vector search
            #     ],
            #     'permission_mode': 'bypassPermissions',
            #     'mcp_servers': {...}  # MCP server with chunk endpoints
            # }
            #
            # async with ClaudeSDKClient(options=agent_options) as client:
            #     await client.query(agent_prompt)
            #
            #     response = ""
            #     async for message in client.receive_response():
            #         if isinstance(message, AssistantMessage):
            #             # Collect response
            #             ...
            #
            # Parse response with existing parser
            # answer_set = AIResponseParser.parse_response(response, question_type, options)
            # return answer_set

        except Exception as e:
            logger.error(f"Error in agent-based QA: {e}")
            raise Exception(f"Agent QA failed: {str(e)}")

    async def _get_question_options(self, question_id: int) -> List[str]:
        """Get options for a SELECT question.

        Args:
            question_id: Question ID

        Returns:
            List of option strings
        """
        options = await self.question_option_service.get_options_for_question(
            question_id
        )
        return [option.value for option in options]


def get_agent_qa_service() -> AgentQAService:
    """Get agent QA service instance.

    Returns:
        AgentQAService instance
    """
    return AgentQAService()
