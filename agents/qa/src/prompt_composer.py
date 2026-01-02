"""
Prompt composition for agent QA.

Composes mega-prompt from three components:
1. Agent orchestration (how to use chunk tools)
2. Analysis style (standard vs correlation, citation requirements)
3. Output format (short answer vs select, JSON structure)
"""

import os
from typing import List, Optional

from ai_config import get_analysis_prompt_file, get_prompt_file
from matrices.matrix_enums import MatrixType
from questions.question_type import QuestionTypeName


def load_prompt(filename: str) -> str:
    """
    Load a prompt from file.

    Args:
        filename: Prompt filename relative to prompts directory

    Returns:
        Prompt content
    """
    # Navigate to project root from this file's location
    # agents/qa/src/prompt_composer.py -> agents/qa/src -> agents/qa -> agents -> root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    prompts_dir = os.path.join(project_root, "prompts")
    filepath = os.path.join(prompts_dir, filename)

    with open(filepath, "r") as f:
        return f.read().strip()


def compose_agent_prompt(
    matrix_type: MatrixType,
    question_type: QuestionTypeName,
    question_text: str,
    document_ids: List[int],
    options: Optional[List[str]] = None,
    min_answers: int = 1,
    max_answers: Optional[int] = 1,
) -> str:
    """
    Compose mega-prompt from three components.

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
    print(
        f"Composing agent prompt: matrix={matrix_type.value}, "
        f"question_type={question_type.name}, docs={len(document_ids)}"
    )

    # Part 1: Agent orchestration (chunk reading strategy)
    orchestration = load_prompt("qa_orchestrator.txt")

    # Part 2: Analysis style (citation requirements, document markers)
    analysis_file = get_analysis_prompt_file(matrix_type)
    analysis = load_prompt(analysis_file)

    # Part 3: Output format (JSON structure)
    output_file = get_prompt_file(question_type)
    output_format = load_prompt(output_file)

    # Part 4: Task context
    doc_list = ", ".join([f"[[document:{doc}]]" for doc in document_ids])

    task_context = f"""# YOUR TASK

**Question:** {question_text}

**Available Documents:** {doc_list}

**Document IDs for MCP tools:** {", ".join(str(d) for d in document_ids)}"""

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
        task_context += f"\n\nProvide between {min_answers} and {max_answers} answers."

    # Compose mega-prompt
    composed = f"""{orchestration}

---

{analysis}

---

{output_format}

---

{task_context}

Begin by using the MCP tools to discover and read relevant chunks, then provide your answer in the required JSON format with proper [[cite:N]] citations and [[document:ID]] markers."""

    print(f"Composed prompt: {len(composed)} characters")
    return composed
