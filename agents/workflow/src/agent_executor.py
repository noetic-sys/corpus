"""
Agent execution for workflow processing.

Handles running the Claude agent and streaming messages.
"""

from typing import Optional

from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, ResultMessage, TextBlock


async def execute_agent(task_prompt: str, options: dict) -> Optional[ResultMessage]:
    """
    Execute Claude agent with given prompt and options.

    Streams agent messages to stdout and returns the final result.

    Args:
        task_prompt: The task prompt to send to the agent
        options: Agent configuration options (including MCP server)

    Returns:
        ResultMessage if execution completes, None if no result received

    Raises:
        Exception: If agent execution fails
    """
    result_message = None

    print("Starting agent execution...")
    print("=" * 80)

    async with ClaudeSDKClient(options=options) as client:
        await client.query(task_prompt)

        async for message in client.receive_response():
            # Log all message types for visibility
            print(f"\n[MESSAGE TYPE: {type(message).__name__}]", flush=True)

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                    else:
                        # Log non-text blocks (tool use, etc)
                        print(f"\n[BLOCK: {type(block).__name__}] {block}", flush=True)
            elif isinstance(message, ResultMessage):
                # Capture result message for final status check
                result_message = message
                print(f"{message}", flush=True)
                print("\n[RESULT DETAILS]", flush=True)
                print(f"  is_error: {message.is_error}", flush=True)
                print(f"  num_turns: {message.num_turns}", flush=True)
                print(f"  duration_ms: {message.duration_ms}", flush=True)
                print(f"  total_cost_usd: {message.total_cost_usd}", flush=True)
                if message.result:
                    print(f"  result: {message.result}", flush=True)
                if message.usage:
                    print(f"  usage: {message.usage}", flush=True)
            else:
                # Log other message types (tool results, errors, etc)
                print(f"{message}", flush=True)

    print("\n" + "=" * 80)
    print("\nAgent execution completed")

    return result_message
