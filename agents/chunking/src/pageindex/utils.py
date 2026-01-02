"""
Utility functions for PageIndex document processing.
"""

import asyncio
import logging
import os
from typing import List, Optional

import anthropic
import tiktoken

from .models import TreeNode

logger = logging.getLogger(__name__)


def count_tokens(text: str, model: Optional[str] = None) -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to tokenize
        model: Model name (unused, kept for compatibility)

    Returns:
        Number of tokens
    """
    if not text:
        return 0

    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


async def call_llm_async(
    model: str,
    prompt: str,
    api_key: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
    max_retries: int = 10,
) -> str:
    """
    Call Anthropic LLM asynchronously with retry logic.

    Args:
        model: Model identifier (e.g., 'claude-3-haiku-20240307')
        prompt: User prompt
        api_key: Anthropic API key (defaults to env var)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        max_retries: Maximum retry attempts

    Returns:
        LLM response text

    Raises:
        Exception: If all retries fail
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    messages = [{"role": "user", "content": prompt}]

    for attempt in range(max_retries):
        try:
            async with anthropic.AsyncAnthropic(api_key=api_key) as client:
                response = await client.messages.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.content[0].text

        except Exception as e:
            logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                logger.error(f"Max retries reached for prompt: {prompt[:100]}...")
                raise


def assign_node_ids(nodes: List[TreeNode], start_id: int = 0) -> int:
    """
    Recursively assign sequential node IDs to tree structure.

    Args:
        nodes: List of tree nodes
        start_id: Starting ID number

    Returns:
        Next available ID

    Raises:
        ValidationError: If nodes is malformed
    """
    node_id = start_id

    for node in nodes:
        node.node_id = str(node_id).zfill(4)
        node_id += 1

        if node.nodes:
            node_id = assign_node_ids(node.nodes, node_id)

    return node_id


def flatten_tree(nodes: List[TreeNode]) -> List[TreeNode]:
    """
    Flatten hierarchical tree into list of nodes.

    Args:
        nodes: Hierarchical tree structure

    Returns:
        Flat list of all nodes (without nested children)
    """
    flat_list: List[TreeNode] = []

    for node in nodes:
        # Create copy without children
        node_copy = node.model_copy(update={"nodes": []})
        flat_list.append(node_copy)

        # Recursively flatten children
        if node.nodes:
            flat_list.extend(flatten_tree(node.nodes))

    return flat_list


def get_leaf_nodes(nodes: List[TreeNode]) -> List[TreeNode]:
    """
    Extract only leaf nodes (nodes without children).

    Args:
        nodes: Hierarchical tree structure

    Returns:
        List of leaf nodes
    """
    leaves: List[TreeNode] = []

    for node in nodes:
        if not node.nodes:
            # Leaf node - make copy without children field
            leaves.append(node.model_copy(update={"nodes": []}))
        else:
            # Recurse into children
            leaves.extend(get_leaf_nodes(node.nodes))

    return leaves


async def generate_node_summary(
    node_text: str, model: str, min_tokens_for_summary: int = 200
) -> str:
    """
    Generate AI summary of node content.

    Args:
        node_text: Text content to summarize
        model: LLM model to use
        min_tokens_for_summary: Min tokens before summarizing (else return text as-is)

    Returns:
        Summary text
    """
    num_tokens = count_tokens(node_text)

    if num_tokens < min_tokens_for_summary:
        return node_text

    prompt = f"""You are given a part of a document. Generate a concise description of the main points covered.

Document Section:
{node_text}

Return only the description, no other text."""

    return await call_llm_async(model, prompt)


def print_tree_toc(nodes: List[TreeNode], indent: int = 0) -> None:
    """
    Print tree structure as table of contents.

    Args:
        nodes: Tree structure
        indent: Current indentation level
    """
    for node in nodes:
        print("  " * indent + node.title)
        if node.nodes:
            print_tree_toc(node.nodes, indent + 1)
