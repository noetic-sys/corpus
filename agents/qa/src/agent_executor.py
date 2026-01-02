"""
Agent execution for QA processing.

Runs the Claude agent and extracts the JSON answer from its response.
"""

from typing import Callable, Optional, Tuple

from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, ResultMessage, TextBlock

from json_extractor import extract_json_from_text, adjust_confidence_in_json


async def execute_agent_with_validation(
    task_prompt: str,
    options: dict,
    validator: Optional[Callable[[str], Tuple[bool, float, str]]] = None,
    max_retries: int = 1,
) -> Tuple[Optional[str], Optional[ResultMessage]]:
    """
    Execute Claude agent with citation validation and retry.

    Maintains conversation context across retry attempts.

    Args:
        task_prompt: The initial task prompt
        options: Agent configuration options
        validator: Optional validation function that returns (should_retry, confidence_multiplier, feedback)
        max_retries: Maximum number of retry attempts (default 1)

    Returns:
        Tuple of (json_answer, result_message)
    """
    result_message = None
    json_answer = None
    attempt = 1

    print("Starting agent QA execution...")
    print("=" * 80)

    async with ClaudeSDKClient(options=options) as client:
        while attempt <= max_retries + 1:
            print(f"\n{'='*80}")
            print(f"ATTEMPT {attempt}/{max_retries + 1}")
            print(f"{'='*80}\n")

            # Query agent (first time with task_prompt, subsequent times with feedback)
            if attempt == 1:
                await client.query(task_prompt)
            # Subsequent attempts handled by validator callback

            # Collect response
            collected_text = []
            async for message in client.receive_response():
                print(f"\n[MESSAGE TYPE: {type(message).__name__}]", flush=True)

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            collected_text.append(block.text)
                            print(block.text, end="", flush=True)
                        else:
                            print(
                                f"\n[BLOCK: {type(block).__name__}] {block}", flush=True
                            )
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

            # Collect full agent response
            # Let AIResponseParser handle extraction - it knows about all formats
            # including <<ANSWER_NOT_FOUND>>, JSON blocks, etc.
            full_text = "".join(collected_text)
            json_answer = extract_json_from_text(full_text)

            if not json_answer:
                print("WARNING: No JSON answer found in agent response")
                print(f"Full response text:\n{full_text}")
                print("================================================================================")
                break

            if json_answer == "<<ANSWER_NOT_FOUND>>":
                print("\nExtracted: <<ANSWER_NOT_FOUND>> (no answer found in documents)")
                # Skip validation - this is a valid terminal state, not an error
                break

            print(f"\nExtracted JSON answer ({len(json_answer)} chars)")

            # Validate if validator provided
            if validator and attempt <= max_retries:
                should_retry, confidence_multiplier, feedback = validator(json_answer)

                if should_retry:
                    print("\nValidation failed, retrying with feedback...")
                    # Query again with feedback (maintains context)
                    await client.query(feedback)
                    attempt += 1
                    continue
                elif confidence_multiplier < 1.0:
                    print(f"\nAdjusting confidence by {confidence_multiplier:.2f}")
                    json_answer = adjust_confidence_in_json(
                        json_answer, confidence_multiplier
                    )

            # Success or max retries reached
            break

    print("\n" + "=" * 80)
    return json_answer, result_message


async def execute_agent(
    task_prompt: str, options: dict
) -> Tuple[Optional[str], Optional[ResultMessage]]:
    """
    Simple agent execution without validation (legacy interface).

    Args:
        task_prompt: The task prompt to send to the agent
        options: Agent configuration options (including MCP server)

    Returns:
        Tuple of (json_answer, result_message)
    """
    return await execute_agent_with_validation(
        task_prompt, options, validator=None, max_retries=0
    )
