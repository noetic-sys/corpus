"""
Agent QA Runner

Entry point for agent-based QA execution in isolated containers.
Orchestrates the full lifecycle:
1. Validate environment
2. Create agent with MCP chunk tools
3. Compose mega-prompt
4. Execute agent
5. Upload answer to API
"""

import asyncio
import sys

from matrices.matrix_enums import MatrixType
from questions.question_type import QuestionTypeName

from agent_config import create_agent_options
from agent_executor import execute_agent_with_validation
from answer_uploader import upload_answer
from answer_validator import (
    build_retry_feedback,
    should_retry,
    validate_answer,
)
from chunk_fetcher import fetch_document_chunks
from env_validator import (
    cleanup_sensitive_env_vars,
    validate_environment,
)
from prompt_composer import compose_agent_prompt


async def main():
    """Main entry point for agent QA execution."""
    # Validate environment
    try:
        (
            qa_job_id,
            matrix_cell_id,
            document_ids,
            question,
            matrix_type_str,
            question_type_id,
            question_id,
            company_id,
            min_answers,
            max_answers,
            options,
            api_endpoint,
            api_key,
            anthropic_api_key,
        ) = validate_environment()
        print(f"Starting agent QA for job {qa_job_id}, cell {matrix_cell_id}")
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Convert types
    try:
        matrix_type = MatrixType(matrix_type_str)
        question_type = QuestionTypeName.from_id(question_type_id)
    except Exception as e:
        print(f"ERROR: Invalid matrix_type or question_type: {e}")
        sys.exit(1)

    # Create agent options with MCP chunk tools
    try:
        agent_options, mcp_tool_names = create_agent_options(
            api_endpoint=api_endpoint,
            api_key=api_key,
            company_id=company_id,
            document_ids=document_ids,
        )
        print(
            f"Generated {len(mcp_tool_names)} MCP tools for chunk reading "
            f"(scoped to {len(document_ids)} documents)"
        )
    except Exception as e:
        print(f"ERROR: Failed to create agent options: {e}")
        sys.exit(1)

    # Fetch document content for citation validation
    try:
        print(
            f"Fetching document content for citation validation ({len(document_ids)} documents)..."
        )
        document_contents = await fetch_document_chunks(
            api_endpoint=api_endpoint,
            api_key=api_key,
            document_ids=document_ids,
        )
        print(
            f"Successfully loaded content for {len(document_contents)}/{len(document_ids)} documents"
        )
        for doc_id, content in document_contents.items():
            print(f"  Document {doc_id}: {len(content)} characters")
    except Exception as e:
        print(f"ERROR: Failed to fetch document content for validation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Compose mega-prompt
    try:
        task_prompt = compose_agent_prompt(
            matrix_type=matrix_type,
            question_type=question_type,
            question_text=question,
            document_ids=document_ids,
            options=options if options else None,
            min_answers=min_answers,
            max_answers=max_answers,
        )
        print(
            f"Composed prompt for {matrix_type.value} matrix, {question_type.name} question"
        )
    except Exception as e:
        print(f"ERROR: Failed to compose prompt: {e}")
        sys.exit(1)

    # Clear sensitive environment variables before agent execution
    cleanup_sensitive_env_vars()

    # Create validator callback
    def citation_validator(answer_json: str):
        """Validate citations and return (should_retry, confidence_multiplier, feedback)."""
        if not document_contents:
            print("WARNING: No document contents available for citation validation")
            return False, 1.0, ""

        validation = validate_answer(answer_json, document_contents)

        print(
            f"\nCitation Validation: avg_score={validation.avg_grounding_score:.2f}, "
            f"ungrounded={len(validation.ungrounded_citations)}/{len(validation.validation_details)}"
        )

        should_retry_answer = should_retry(validation)
        feedback = build_retry_feedback(validation) if should_retry_answer else ""

        return should_retry_answer, validation.avg_grounding_score, feedback

    # Execute agent with validation
    try:
        json_answer, result_message = await execute_agent_with_validation(
            task_prompt=task_prompt,
            options=agent_options,
            validator=citation_validator if document_contents else None,
            max_retries=1,
        )

        if not json_answer:
            print("ERROR: No JSON answer extracted from agent response")
            sys.exit(1)

        if result_message and result_message.is_error:
            print(f"ERROR: Agent execution failed: {result_message.result}")
            sys.exit(1)

    except Exception as e:
        print(f"ERROR: Agent execution failed: {e}")
        sys.exit(1)

    # Upload answer to API (api_key still in scope, not in env)
    try:
        upload_answer(
            api_endpoint=api_endpoint,
            api_key=api_key,
            qa_job_id=qa_job_id,
            matrix_cell_id=matrix_cell_id,
            question_type_id=question_type_id,
            answer_json=json_answer,
        )
        print(f"Successfully uploaded answer for QA job {qa_job_id}")
    except Exception as e:
        print(f"ERROR: Failed to upload answer: {e}")
        sys.exit(1)
    sys.exit(1)

    print("Agent QA execution completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
