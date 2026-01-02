"""
Agent execution for document chunking.

Handles running the Claude agent for chunking documents.
"""

import os
from typing import Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)


def load_prompt(filename: str) -> str:
    """Load prompt from file."""
    prompts_dir = "/app/prompts"
    filepath = os.path.join(prompts_dir, filename)
    with open(filepath, "r") as f:
        return f.read().strip()


async def execute_chunking_agent(
    document_id: int, document_path: str, output_dir: str
) -> Optional[ResultMessage]:
    """
    Execute Claude agent to chunk document.

    Args:
        document_id: Document ID
        document_path: Path to document file
        output_dir: Output directory for chunks

    Returns:
        ResultMessage if execution completes, None if no result received

    Raises:
        Exception: If agent execution fails
    """
    # Load prompts
    chunker_system_prompt = load_prompt("document_chunker.txt")
    task_prompt_template = load_prompt("document_chunker_task.txt")

    task_prompt = task_prompt_template.format(
        document_path=document_path, output_dir=output_dir, document_id=document_id
    )

    # Configure agent with file system tools
    chunker_options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Glob", "Grep"],
        permission_mode="bypassPermissions",
        system_prompt=chunker_system_prompt,
        model="haiku",  # Fast, cheap for mechanical task
    )

    result_message = None

    print(f"Starting chunking agent for document {document_id}...")
    print("=" * 80)

    async with ClaudeSDKClient(options=chunker_options) as client:
        await client.query(task_prompt)

        async for message in client.receive_response():
            print(f"\n[MESSAGE TYPE: {type(message).__name__}]", flush=True)

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                    else:
                        print(f"\n[BLOCK: {type(block).__name__}] {block}", flush=True)
            elif isinstance(message, ResultMessage):
                result_message = message
                print(f"{message}", flush=True)
                print("\n[RESULT DETAILS]", flush=True)
                print(f"  is_error: {message.is_error}", flush=True)
                print(f"  num_turns: {message.num_turns}", flush=True)
                print(f"  duration_ms: {message.duration_ms}", flush=True)
                print(f"  total_cost_usd: {message.total_cost_usd}", flush=True)
            else:
                print(f"{message}", flush=True)

    print("\n" + "=" * 80)
    print("\nChunking agent completed")

    return result_message
